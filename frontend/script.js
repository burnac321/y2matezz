const BACKEND_API = 'https://your-railway-app.up.railway.app';

class VideoDownloader {
    async getFormats(videoUrl) {
        const response = await fetch(`${BACKEND_API}/get_formats`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: videoUrl })
        });
        return await response.json();
    }

    async getDirectUrl(videoUrl, formatId) {
        const response = await fetch(`${BACKEND_API}/get_direct_url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                url: videoUrl, 
                format_id: formatId 
            })
        });
        return await response.json();
    }
}

// ... rest of your frontend code from previous examples
