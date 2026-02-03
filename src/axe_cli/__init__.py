from loguru import logger

# Disable logging by default for library usage.
# Application entry points (e.g., axe_cli.cli) should call logger.enable("axe_cli")
# to enable logging.
logger.disable("axe_cli")
