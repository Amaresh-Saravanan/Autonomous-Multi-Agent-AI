This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## MapLibre worker files (`public/maplibre-gl-*.mjs`)

`maplibre-gl` v6 builds its tile-processing Worker URL from a
dynamically-constructed `new URL(..., import.meta.url)` path, which no
bundler (confirmed: both webpack and Turbopack) can statically resolve to
copy into the build — the worker silently 404s and the map never renders,
with no error surfaced anywhere. `public/maplibre-gl-worker.mjs` and
`public/maplibre-gl-shared.mjs` are **manual copies** of
`node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs` and
`maplibre-gl-shared.mjs`, wired up via `setWorkerUrl()` in
`components/MapView.tsx`. **Re-copy both files after every `maplibre-gl`
version bump** — nothing keeps them in sync automatically.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
