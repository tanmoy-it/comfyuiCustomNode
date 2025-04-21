# Import the node class definitions
from .download_image_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Define the web directory for JavaScript files
WEB_DIRECTORY = "./js"

# Export the mappings and web directory
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

print("### Loading Custom Nodes: Download Image (Direct/No Save) ###")