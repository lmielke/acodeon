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

table_max_chars = 100

resources_dir = os.path.expanduser(f'~{os.sep}.{package_name}')
if not os.path.exists(resources_dir):
    os.makedirs(resources_dir)

# the following directories refer to the temporary package structure and logs
# the resulting paths depend on the work_path or cwd this package is run inside
# all process files are stored here
temp_dir = lambda pg_name: os.path.join(resources_dir, 'cr_logs', pg_name)
# all cr_prompt files are stored here
cr_prompt_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_prompt_files')
cr_prompt_file_name = lambda file_name, cr_id: f'cr_{cr_id}_{file_name.split(".")[0]}.md'
cq_ex_llm_file = os.path.join(resources_dir, 'CQ-EX-LLM.md')
# all cr_integration_files are staged here
cr_integration_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_integration_files')
cr_integration_archived_name = lambda file_name, cr_id: f'cr_{cr_id}_{file_name.split('.')[0]}.py'
stage_files_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'stage_files')
json_files_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_json_files')
json_file_name = lambda file_name, cr_id: f'cr_{cr_id}_{file_name.split('.')[0]}.json'
restore_files_dir = lambda pg_name: os.path.join(temp_dir(pg_name), f'{pg_name}_archive')

json_target, json_content = 'target', 'code'
exists_status = 'already exists'

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
