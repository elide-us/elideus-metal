import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(() => {
	return {
    	plugins: [react()],
   		base: '/static/',
    	build: {
      		outDir: 'static',
      		assetsDir: 'assets',
  		}
	}
})
