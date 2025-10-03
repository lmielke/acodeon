# settings.py
import os, re, sys, time, yaml
from datetime import datetime as dt

package_name = "codeon"
package_dir = os.path.dirname(__file__)
project_dir = os.path.dirname(package_dir)
project_name = os.path.basename(project_dir)

apis_dir = os.path.join(package_dir, "apis")
apis_json_dir = os.path.join(package_dir, "apis", "json_schemas")

test_dir = os.path.join(package_dir, "test")
test_data_dir = os.path.join(test_dir, "data")

time_stamp = lambda: dt.now().strftime("%Y-%m-%d-%H-%M-%S")
session_time_stamp = time_stamp()

ignore_dirs = {
    ".git",
    "build",
    "gp",
    "dist",
    "models",
    "*.egg-info",
    "__pycache__",
    ".pytest_cache",
    ".tox",
}
abrev_dirs = {
    "log",
    "logs",
    "testopia_logs",
    "chat_logs",
}

# for some purposes file content has to be displayed to the user
# some technical files should be excluded here up to a certain verbosity
# Note: Readme.md is always included which it is put inside the ix 99 block
ignore_files = {
    5: {
        'CHANGELOG.md',
        'LICENSE',
        'MANIFEST.in',
        'testhelper.py',
        '__init__.py',
        'server.pyw',
        'info.py',
    },
    6: {
        'Pipfile.lock',
        '.gitignore',
    },
    7: {
        '.sublime-',
    },
    99: {
        'Readme.md',
        '.png',
        '.jpg',
        '.jpeg',
        '.gif',
        '.bmp',
        '.tiff',
    },
}

resources_dir = os.path.expanduser(f'~{os.sep}.{package_name}')
if not os.path.exists(resources_dir):
    os.makedirs(resources_dir)

update_logs_dir = os.path.join(resources_dir, 'update_logs')
update_logs_temp_dir_name = 'temp_files'
update_temp_dir = os.path.join(resources_dir, update_logs_temp_dir_name)
update_logs_op_code_files_dir_name = 'op_code_files'
update_temp_test_dir = os.path.join(update_logs_dir, package_name, update_logs_temp_dir_name)
print(f"{update_temp_test_dir = }")
update_logs_test_dir = os.path.join(update_logs_dir, package_name, update_logs_op_code_files_dir_name)

user_settings_name = "settings.yml"
user_settings_path = os.path.join(resources_dir, user_settings_name)
if not os.path.exists(user_settings_path):
    with open(user_settings_path, 'w') as f:
        yaml.dump({'package_name': package_name, 'port': 9007}, f)

# Load user settings from resources YAML file
def load_user_settings():
    """Load user settings from the YAML file."""
    if not os.path.exists(user_settings_path):
        return {}

    with open(user_settings_path, 'r') as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error loading user settings: {e}")
            return {}

# we add user settings to the global namespace
user_settings = load_user_settings()
# Update the global namespace with user settings
globals().update(user_settings)
