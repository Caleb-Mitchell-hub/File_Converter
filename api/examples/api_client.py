"""DocConverter API 同步客户端封装。

本模块提供了一个轻量的同步 HTTP 客户端，封装了 DocConverter 后端的 REST 接口。
基于 ``requests.Session``，支持上下文管理与连接复用。

典型用法::

    with DocConverterClient() as client:
        # 健康检查
        info = client.health()
        print(info["status"])

        # 单文件转换，并自动下载到本地
        result = client.convert_single(
            file_path="sample.png",
            conversion_type="png_to_pdf",
            save_to="out.pdf",
        )

        # 批量转换（异步）
        task_id = client.convert_batch(
            file_paths=["a.png", "b.png"],
            conversion_type="png_to_pdf",
            zip_output=True,
        )

        # 轮询直到完成
        def on_progress(info):
            print(f"{info['progress']:.1f}% - {info['status']}")

        final = client.wait_for_task(task_id, on_progress=on_progress)

        # 下载批量结果（ZIP）
        client.download(task_id, save_to="result.zip")

错误约定：
    - 所有非 2xx 的 HTTP 响应都会抛 :class:`APIError`。
    - 客户端层面的超时/连接错误保持 ``requests`` 原生异常语义。
"""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Callable, Optional, Union

import requests


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------


class APIError(RuntimeError):
    """DocConverter API 调用错误。

    当服务端返回非 2xx 响应时抛出。除消息外，保留 ``status_code`` 与
    ``response_body`` 以便上层做更精细的判断。
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_body: Any = None,
        url: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.url = url

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return (
            f"APIError(status_code={self.status_code!r}, "
            f"message={str(self)!r}, url={self.url!r})"
        )


# ---------------------------------------------------------------------------
# 客户端
# ---------------------------------------------------------------------------


# 进度回调签名：``Callable[[dict], None]``
ProgressCallback = Callable[[dict], None]


class DocConverterClient:
    """DocConverter REST API 的同步封装。

    所有方法都返回解析后的 JSON（``dict`` / ``list``），HTTP 错误统一抛
    :class:`APIError`。批量任务的下载和轮询也在本类中。

    支持 ``with`` 上下文管理::

        with DocConverterClient() as client:
            ...
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 300) -> None:
        """初始化客户端。

        Args:
            base_url: API 根地址，例如 ``http://localhost:8000``。
            timeout: 单次请求的超时（秒），大文件转换需要适当调大。
        """
        self.base_url: str = base_url.rstrip("/")
        self.timeout: int = timeout
        self._session: requests.Session = requests.Session()

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """拼接完整 URL。``path`` 必须以 ``/`` 开头。"""
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _check(self, resp: requests.Response) -> dict:
        """检查响应状态码并提取 JSON。

        Args:
            resp: ``requests`` 响应对象。

        Returns:
            解析后的 JSON。

        Raises:
            APIError: 状态码非 2xx 时。
        """
        if not (200 <= resp.status_code < 300):
            # 尽量解析 JSON 错误体，回退到原始文本
            try:
                body: Any = resp.json()
            except ValueError:
                body = resp.text
            raise APIError(
                f"API {resp.request.method if resp.request else 'REQUEST'} "
                f"{resp.url} failed: {resp.status_code} {resp.reason}",
                status_code=resp.status_code,
                response_body=body,
                url=resp.url,
            )
        # 204 / 空体防御
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError as exc:
            raise APIError(
                f"无法解析响应 JSON: {exc}",
                status_code=resp.status_code,
                response_body=resp.text,
                url=resp.url,
            ) from exc

    @staticmethod
    def _open_file(file_path: Union[str, Path]) -> tuple[str, Any, Optional[str]]:
        """打开待上传文件，返回 ``(filename, file_obj, mimetype)``。

        注意：调用方负责关闭文件对象。
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"找不到待上传文件: {p}")
        # 优先用 stem + 原后缀，避免不同扩展名导致的服务器解析问题
        filename = p.name
        mime, _ = mimetypes.guess_type(p.name)
        # ``open`` 后再交由 requests 读取；显式 ``rb`` 保证二进制安全
        return filename, open(p, "rb"), mime

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------

    def health(self) -> dict:
        """健康检查。

        Returns:
            形如 ``{"status": "ok", "supported_pairs": N, ...}`` 的字典。
        """
        resp = self._session.get(
            self._url("/api/v1/health"),
            timeout=self.timeout,
        )
        return self._check(resp)

    # ------------------------------------------------------------------
    # 单文件转换
    # ------------------------------------------------------------------

    def convert_single(
        self,
        file_path: Union[str, Path],
        conversion_type: str,
        *,
        target_filename: Optional[str] = None,
        dpi: Optional[int] = None,
        jpg_quality: Optional[int] = None,
        overwrite: bool = False,
        save_to: Optional[Union[str, Path]] = None,
    ) -> dict:
        """单文件转换。

        Args:
            file_path: 源文件路径。
            conversion_type: 转换类型枚举字符串，例如 ``"xlsx_to_pdf"``。
            target_filename: 自定义输出文件名（不含路径）。
            dpi: 输出图片 DPI（仅图片相关转换生效）。
            jpg_quality: JPG 质量 1-100。
            overwrite: 是否覆盖已存在的目标。
            save_to: 若指定，会自动调用 :meth:`download` 将结果下载到该路径。

        Returns:
            服务端 ``data`` 字段的字典，常包含 ``output_filename``、
            ``file_size``、``duration`` 等。
        """
        data: dict[str, Any] = {
            "conversion_type": conversion_type,
            "overwrite": "true" if overwrite else "false",
        }
        if target_filename is not None:
            data["target_filename"] = target_filename
        if dpi is not None:
            data["dpi"] = str(dpi)
        if jpg_quality is not None:
            data["jpg_quality"] = str(jpg_quality)

        filename, file_obj, mime = self._open_file(file_path)
        try:
            files = {"file": (filename, file_obj, mime)}
            resp = self._session.post(
                self._url("/api/v1/convert"),
                data=data,
                files=files,
                timeout=self.timeout,
            )
            payload = self._check(resp)
        finally:
            file_obj.close()

        # 业务层 ``data`` 字段透传；若服务端把 data 嵌在 envelope 里则一并剥离
        result = payload.get("data", payload) if isinstance(payload, dict) else payload

        if save_to is not None:
            # 单文件接口的 task_id 一般与 file 关联；优先取 ``task_id`` 字段
            task_id = None
            if isinstance(result, dict):
                task_id = result.get("task_id")
            if task_id is None:
                raise APIError(
                    "save_to 已指定，但响应中未找到 task_id，无法下载。",
                    status_code=200,
                    response_body=result,
                )
            self.download(task_id, save_to=save_to)

        return result

    # ------------------------------------------------------------------
    # 批量转换
    # ------------------------------------------------------------------

    def convert_batch(
        self,
        file_paths: list[Union[str, Path]],
        conversion_type: str,
        *,
        target_subdir: Optional[str] = None,
        dpi: Optional[int] = None,
        jpg_quality: Optional[int] = None,
        zip_output: bool = True,
    ) -> str:
        """提交批量转换任务，立即返回 ``task_id``。

        任务在服务端异步执行，需配合 :meth:`wait_for_task` 与
        :meth:`download` 完成后续处理。

        Args:
            file_paths: 待转换文件路径列表。
            conversion_type: 转换类型枚举字符串。
            target_subdir: 输出子目录名（批量任务内使用）。
            dpi: 输出图片 DPI。
            jpg_quality: JPG 质量。
            zip_output: 是否打包成 zip（默认 True）。

        Returns:
            ``task_id`` 字符串。

        Raises:
            ValueError: 文件列表为空时。
        """
        if not file_paths:
            raise ValueError("file_paths 不能为空")

        data: dict[str, Any] = {
            "conversion_type": conversion_type,
            "zip_output": "true" if zip_output else "false",
        }
        if target_subdir is not None:
            data["target_subdir"] = target_subdir
        if dpi is not None:
            data["dpi"] = str(dpi)
        if jpg_quality is not None:
            data["jpg_quality"] = str(jpg_quality)

        # 按 multipart 规范批量文件
        files: list[tuple[str, tuple[str, Any, Optional[str]]]] = []
        opened: list[Any] = []
        try:
            for fp in file_paths:
                fname, fobj, mime = self._open_file(fp)
                opened.append(fobj)
                files.append(("files", (fname, fobj, mime)))

            resp = self._session.post(
                self._url("/api/v1/convert/batch"),
                data=data,
                files=files,
                timeout=self.timeout,
            )
            payload = self._check(resp)
        finally:
            for fobj in opened:
                fobj.close()

        # 兼容两种返回结构：``{"data": {"task_id": ...}}`` 或 ``{"task_id": ...}``
        if isinstance(payload, dict) and "task_id" in payload:
            return str(payload["task_id"])
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            return str(payload["data"]["task_id"])
        raise APIError(
            "批量任务响应缺少 task_id 字段",
            status_code=200,
            response_body=payload,
        )

    # ------------------------------------------------------------------
    # 任务查询 / 轮询
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> dict:
        """查询任务状态。

        Args:
            task_id: 任务 ID。

        Returns:
            任务信息字典。
        """
        resp = self._session.get(
            self._url(f"/api/v1/tasks/{task_id}"),
            timeout=self.timeout,
        )
        return self._check(resp)

    def wait_for_task(
        self,
        task_id: str,
        *,
        poll_interval: float = 1.0,
        timeout: Optional[float] = None,
        on_progress: Optional[ProgressCallback] = None,
    ) -> dict:
        """轮询直到任务完成（成功或失败）。

        Args:
            task_id: 任务 ID。
            poll_interval: 轮询间隔（秒）。
            timeout: 总超时（秒），``None`` 表示无限等待。
            on_progress: 进度回调，签名 ``(task_info: dict) -> None``。
                每次轮询触发一次，回调内应自行处理异常（不会回传到本方法）。

        Returns:
            最终的任务信息字典（``status`` 已为终态）。

        Raises:
            TimeoutError: 超过 ``timeout`` 仍未完成。
            RuntimeError: 任务最终 ``status`` 为 ``failed``。
        """
        if poll_interval <= 0:
            raise ValueError("poll_interval 必须 > 0")
        started = time.monotonic()
        last_info: dict = {}

        while True:
            info = self.get_task(task_id)
            last_info = info if isinstance(info, dict) else last_info

            if on_progress is not None and isinstance(info, dict):
                try:
                    on_progress(info)
                except Exception:  # noqa: BLE001 - 回调错误不应影响轮询主循环
                    pass

            status = info.get("status") if isinstance(info, dict) else None
            if status in ("success", "partial_success", "failed", "cancelled"):
                if status == "failed":
                    raise RuntimeError(
                        f"任务 {task_id} 失败: {info.get('error') or info}"
                    )
                return info

            if timeout is not None and (time.monotonic() - started) > timeout:
                raise TimeoutError(
                    f"等待任务 {task_id} 超时（>{timeout}s），最新 status={status}"
                )
            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # 下载
    # ------------------------------------------------------------------

    def download(
        self,
        task_id: str,
        save_to: Union[str, Path],
        filename: Optional[str] = None,
    ) -> Path:
        """下载任务结果。

        Args:
            task_id: 任务 ID。
            save_to: 保存路径（文件路径而非目录）。
            filename: 批量任务中指定文件名；单文件任务无需。

        Returns:
            实际保存的本地 :class:`Path`。

        Raises:
            FileNotFoundError: 服务端返回 404 时同样会抛 :class:`APIError`。
        """
        if filename:
            url = self._url(f"/api/v1/tasks/{task_id}/download/{filename}")
        else:
            url = self._url(f"/api/v1/tasks/{task_id}/download")

        with self._session.get(url, timeout=self.timeout, stream=True) as resp:
            if not (200 <= resp.status_code < 300):
                # 释放连接并复用通用错误处理
                try:
                    body: Any = resp.json()
                except ValueError:
                    body = resp.text
                raise APIError(
                    f"下载失败: {resp.status_code} {resp.reason}",
                    status_code=resp.status_code,
                    response_body=body,
                    url=resp.url,
                )

            dest = Path(save_to)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
        return dest

    # ------------------------------------------------------------------
    # 任务列表 / 删除
    # ------------------------------------------------------------------

    def list_tasks(self, limit: int = 50) -> list:
        """列出最近任务。

        Args:
            limit: 最多返回多少条记录。

        Returns:
            任务信息列表。
        """
        resp = self._session.get(
            self._url("/api/v1/tasks"),
            params={"limit": limit},
            timeout=self.timeout,
        )
        payload = self._check(resp)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return payload["data"]
        return []

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其结果。

        Args:
            task_id: 任务 ID。

        Returns:
            服务端返回 success 时为 ``True``，否则 ``False``。
        """
        resp = self._session.delete(
            self._url(f"/api/v1/tasks/{task_id}"),
            timeout=self.timeout,
        )
        try:
            payload = self._check(resp)
        except APIError:
            return False
        if isinstance(payload, dict):
            if "success" in payload:
                return bool(payload["success"])
            return True
        return True

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭底层 session。"""
        self._session.close()

    def __enter__(self) -> "DocConverterClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
