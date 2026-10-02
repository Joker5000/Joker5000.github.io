import uvicorn
from .config import settings

if __name__=="__main__":
    uvicorn.run("app.web:app",host="0.0.0.0",port=settings.web_port,proxy_headers=True)
