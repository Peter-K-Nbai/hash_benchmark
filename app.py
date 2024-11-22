import helpers
import logging
import time
import asyncio
from a2wsgi import ASGIMiddleware
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.responses import PlainTextResponse

# Set up logging to file
LOG_FILE_PATH = "app.log"
HASHCAT_OUT_FILE_PATH = "hashcat.out"
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler(LOG_FILE_PATH)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Redirect Uvicorn and FastAPI logs to the same log file
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.addHandler(file_handler)

fastapi_app = FastAPI()

# Global variable to store start time
START_TIME = time.time()

# Set up async lifespan for starting the benchmark
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the benchmark in the background
    logger.info("Starting the async Hashcat benchmark.")
    asyncio.create_task(helpers.run_hashcat_benchmark(logger))
    yield  # Control passes back to FastAPI to continue app startup
    # (Any cleanup logic would go here if needed)

fastapi_app = FastAPI(lifespan=lifespan)

# Define route in FastAPI to expose original functionality
@fastapi_app.get("/check_gpu")
async def check_gpu():
    try:
        gpu_count = helpers.get_gpu_count()
        return {"message": "Got GPU count", "count": gpu_count}
    except Exception as e:
        logger.error(f"Error in check_gpu: {e}")
        return {"message": "An error occurred"}

@fastapi_app.get("/check_gpu_memory")
async def check_gpu_memory():
    try:
        gpu_mem_info = helpers.get_gpu_memory()
        if gpu_mem_info:
            return {"message": "Got GPU memory info", "gpu_mem_info": gpu_mem_info}
        else:
            return {"message": "Could not get GPU memory info"}
    except Exception as e:
        logger.error(f"Error in check_gpu_memory: {e}")
        return {"message": "An error occurred"}

@fastapi_app.get("/")
@fastapi_app.get("/result")
async def get_info():
    try:
        # Call the async functions and await them
        benchmark_avg = await helpers.calculate_average_benchmark()  # Await because it's async
        unknown_count = await helpers.get_unknown_counts()  # Await because it's async

        # If benchmark_avg is None, print None and return it
        if benchmark_avg is None:
            logger.error("Benchmark data is None")
            return {"message": "Benchmark data is None", "data": None}

        if unknown_count is None:
            logger.error("Unknown count data is None")
            return {"message": "Unknown count data is None", "data": None}
        
        # gpu_count = {'gpu_count': helpers.get_gpu_count()}


        # Calculate time elapsed
        time_elapsed = {"time_elapsed": (time.time() - START_TIME)}

        # Create the data structure for the response
        # data = [benchmark_avg, unknown_count, time_elapsed, gpu_count, helpers.get_gpu_memory()]

        data={
            "type":"hash",
            "rpm": benchmark_avg["average_hash_rate"]*60,
            "elapsed_sec": time_elapsed["time_elapsed"],
            "total_gpu_memory_gib": helpers.get_gpu_memory()[0]["total_memory_MB"]/1024
        }

        return {"message": "Got info", "data": data}
    
    except Exception as e:
        logger.error(f"Error in get_info: {e}")
        return {"message": "An error occurred", "error": str(e)}

@fastapi_app.get("/hashcat_out", response_class=PlainTextResponse)
def get_hashcat_out():
    try:
        with open(HASHCAT_OUT_FILE_PATH, "r") as log_file:
            log_content = log_file.read()
        return log_content
    except Exception as e:
        logger.error(f"Error in fetching logs: {e}")
        return PlainTextResponse("An error occurred while reading the log file.", status_code=500)

@fastapi_app.get("/logs", response_class=PlainTextResponse)
async def get_logs():
    try:
        with open(LOG_FILE_PATH, "r") as log_file:
            log_content = log_file.read()
        return log_content
    except Exception as e:
        logger.error(f"Error in fetching logs: {e}")
        return PlainTextResponse("An error occurred while reading the log file.", status_code=500)

# Main entry point to run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=5000, log_config=None)
