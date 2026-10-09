# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR. Linting and formatting are handled by [Biome](https://biomejs.dev).

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Lint and format (Biome)

The project uses [Biome](https://biomejs.dev) for both linting and formatting, configured in `biome.jsonc`:

```sh
npm run lint     # biome check .
npm run format   # biome check --write .
```

See the [Biome rules documentation](https://biomejs.dev/linter/) for the full list of rules and categories.
