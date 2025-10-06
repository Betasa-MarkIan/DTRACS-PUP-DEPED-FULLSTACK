from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.logging import AccessFormatter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging
import sys
import ipaddress
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout) 
    ]
)

logger = logging.getLogger(__name__)
sys.path.append("src")

from exceptions import ExceptionDict
from route import school_routes, focal_routes, admin_routes
from auth import auth_route, auth_security
from database.database import engine, Base, get_db
from database.redis import get_redis_client
from config.config import settings

class RealIPAccessFormatter(AccessFormatter):
    def formatMessage(self, record):
        if isinstance(record.args, dict):
            real_ip = record.args.get("real_ip")
            if real_ip:
                record.args["client_addr"] = real_ip
        return super().formatMessage(record)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Database initialization"""
    async with engine.begin() as conn:
        #await conn.run_sync(Base.metadata.drop_all)  #! Uncomment to reset database
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")
    
    """Redis initialization"""
    global redis_client
    redis_client = await get_redis_client()
    print("✅ Redis client initialized successfully")

    """Logger configuration"""    
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RealIPAccessFormatter(
        fmt='%(client_addr)s - [%(asctime)s] "%(request_line)s" %(status_code)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    access_logger.addHandler(handler)
    access_logger.propagate = False

    """Scheduler initializaiton"""
    auth_security.scheduler.start()

    yield

    await engine.dispose()
    await redis_client.close()
    auth_security.scheduler.shutdown()
    print("Database connection closed")


exc = ExceptionDict()
app = FastAPI(
    title="DEPED-BINAN: School Monitoring and Compliance System",
    description="api",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redocs",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        settings.ADMIN_FRONTEND_URL,
        "https://focal-trainer-recognized-brussels.trycloudflare.com",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3000",       
        ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)

def get_real_client_ip(request: Request) -> str:
    """
    Extract the real client IP address for Railway deployment
    Railway uses X-Forwarded-For header with the client IP as first value
    """
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "CF-Connecting-IP",
        "True-Client-IP",
    ]
    for header in ip_headers:
        ip = request.headers.get(header)
        if ip:
            if "," in ip:
                ip = ip.split(",")[0].strip()
            try:
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def extract_real_ip(request: Request, call_next):
    real_ip = get_real_client_ip(request)
    request.state.real_ip = real_ip
    old_client = request.scope.get("client") or (None, None)
    port = old_client[1]
    if real_ip:
        request.scope["client"] = (real_ip, port)

    response = await call_next(request)
    return response


@app.get("/whats-my-ip")
async def whats_my_ip(request: Request):
    client_host = request.client.host if request.client else None
    real_ip = getattr(request.state, "real_ip", None)
    headers_info = {}
    ip_headers = [
        "X-Forwarded-For", 
        "X-Real-IP", 
        "CF-Connecting-IP", 
        "True-Client-IP",
        "X-Original-Forwarded-For",
    ]
    for header in ip_headers:
        headers_info[header] = request.headers.get(header)
    return {
        "client_host": client_host,
        "real_ip_from_middleware": real_ip,
        "ip_headers": headers_info,
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    }


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """ Endpoint to test database and redis connectivity"""
    try:
        result = await db.execute(text("SELECT 1"))
        db_status = "connected" if result.scalar() == 1 else "disconnected"
        redis_status = "connected"
        try:
            await redis_client.ping()
        except:
            redis_status = "disconnected"
        return {
            "status": "healthy", 
            "database": db_status,
            "redis": redis_status,
            "message": "API, database, and Redis are running successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


app.include_router(auth_route.router)
app.include_router(school_routes.router)
app.include_router(focal_routes.router)
app.include_router(admin_routes.router)


async def exc_handler(req, exc):
    return JSONResponse(
        status_code = getattr(exc, 'status_code', status.HTTP_500_INTERNAL_SERVER_ERROR),
        content = {"message": getattr(exc, 'detail', str(exc))}
    )  

for exc_name in [
    "AccountNotFound",
    "AccountRegistrationFailed",
    "InvalidCredentials",
    "UpdateFailed",
    "NoTaskFound",
    "RetrievingTasksFailed",
    "DatabaseError",
    "AccountDuplication",
    "TaskCreationFailed",
]:
    app.add_exception_handler(exc.get_class(exc_name), exc_handler)
    
app.add_exception_handler(HTTPException, exc_handler)
app.add_exception_handler(Exception, exc_handler)


def main():
    """Start the application in production mode"""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=True)

def dev():
    """Start the application in development mode"""
    import uvicorn
    uvicorn.run("main:app", host="127.8.8.1", port=8000, reload=True)

if __name__ == "__main__":
    main()

