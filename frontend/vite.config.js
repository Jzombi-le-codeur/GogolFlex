import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// AJOUT : "({ mode }) =>" pour transformer l'objet en fonction
export default defineConfig(({ mode }) => {
    // Load env
    const env = loadEnv(mode, process.cwd(), "");

    return {
        plugins: [react()],
        server: {
            // Dev Server's Informations
            host: env.HOST || '0.0.0.0',
            port: parseInt(env.PORT) || 80,

            // Config proxy
            proxy: {
                "/api": {
                    target: `http://${env.API_HOST}:${env.API_PORT}`,
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/api/, ''),
                }
            }
        }
    }
})
