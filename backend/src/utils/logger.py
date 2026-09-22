import logging
import sys

# Configure standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("spreego")


def log_mock_otp(identifier: str, otp_code: str) -> None:
    """
    Log mock OTP to console/stdout for testing and development.
    Uses both stdout print and structured logger to ensure visibility in all test fixtures.
    """
    message = f"[MOCK OTP SERVICE] OTP for {identifier}: {otp_code}"
    print(message, flush=True)
    logger.info(message)
