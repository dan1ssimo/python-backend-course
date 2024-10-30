from fastapi import FastAPI, status

from hw3.demo_service.api import users, utils
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="Testing Demo Service",
    lifespan=utils.initialize,
)

app.add_exception_handler(ValueError, utils.value_error_handler)
app.include_router(users.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


Instrumentator().instrument(app).expose(app)