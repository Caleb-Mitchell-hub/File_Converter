/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_API_BASE: string
  readonly VITE_API_PREFIX: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
