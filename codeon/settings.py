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
test_cr_ids = {"9999-99-99-99-99-99", "8888-88-88-88-88-88"}

time_stamp = lambda: dt.now().strftime("%Y-%m-%d-%H-%M-%S")
session_time_stamp = time_stamp()
time_stamp_regex = r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}"
cr_id_regex = rf"cr_({time_stamp_regex})_"
to_dt = lambda ts: dt.strptime(ts, "%Y-%m-%d-%H-%M-%S")
# match to dict cr_id, file_name, file_ext from a file-name like cr_2024-01-31-12-30-45_example.py
# cr files can be markdown or json or python files
cr_file_name_exts = {'md', 'json', 'py'}
file_name_regex = rf"^(?P<name>[\w.-]+?)(?P<ext>\.\w+)$"
cr_file_regex = rf"cr_(?P<cr_id>{time_stamp_regex})_(?P<file_name>\w+\.(?:{'|'.join(cr_file_name_exts)}))"

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
    "helpers",
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
# cr_headers
pg_header_regex = r"(#--- cr_op:.*?---#)"
unit_header_regex = r"(#-- cr_op:.*?--#)(.*?)(?=#--|$)"
md_fence_regex = r"^\s*```[a-zA-Z]*\n|(\n\s*```\s*$)"
# the following directories refer to the temporary package structure and logs
# the resulting paths depend on the work_path or cwd this package is run inside
# all process files are stored here
integration_formats = {
    'md': '__integration_file__',
    'json': '__integration_json__',
}

phases = ('prompt', 'json', 'integration', 'processing')# cr_finalizing

integration_file_templ_path = os.path.join(resources_dir, 'integration_file_template.md')
cq_ex_llm_file = os.path.join(resources_dir, 'CQ-EX-LLM.md')
temp_dir = lambda pg_name: os.path.join(resources_dir, pg_name)
# do not change order here
# all prompt_string files are stored here
prompt_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'prompts')
prompt_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.md'
# all json_files are staged here
json_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'jsons')
json_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split('.')[0]}.json'
# all integration_files are staged here
integration_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'integrations')
integration_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split('.')[0]}.py'
# staging dir for source update files
processing_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'processing')
processing_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'
# restoring overwritten source files is done from here
restore_dir = lambda pg_name: os.path.join(temp_dir(pg_name), f'{pg_name}_archive')
restore_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'
# all cr meta data is logged here
logs_dir = lambda pg_name: os.path.join(temp_dir(pg_name), f'logs')
log_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'
# all warnings or errors are loged in logs_dir
error_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}_error.log'
error_path = None # to be set later

cr_paths = {
    'prompt_path': (prompt_dir, prompt_file_name),
    'json_path': (json_dir, json_file_name),
    'integration_path': (integration_dir, integration_file_name),
    'processing_path': (processing_dir, processing_file_name),
    'restore_path': (restore_dir, restore_file_name),
    'log_path': (logs_dir, log_file_name),
    'error_path': (logs_dir, error_file_name),
}

file_exists_default = 'NEW'

target_key, content_key = 'target', 'code'
# exists_status = 'already exists'

user_settings_name = "settings.yml"
user_settings_path = os.path.join(resources_dir, user_settings_name)
if not os.path.exists(user_settings_path):
    with open(user_settings_path, 'w') as f:
        yaml.dump({'package_name': package_name, 'port': 9007}, f)

cr_settings_name = "cr_settings.yml"
cr_settings_path = os.path.join(resources_dir, cr_settings_name)
if not os.path.exists(cr_settings_path):
    with open(cr_settings_path, 'w') as f:
        yaml.dump({'cr_snippets': 'empty'}, f)

# Load user settings from resources YAML file
def load_settings(path):
    """Load user settings from the YAML file."""
    if not os.path.exists(path):
        return {}

    with open(path, 'r') as f:
        try:
            st = yaml.safe_load(f) or {}
            return {k: vs.strip() if type(vs) == str else vs for k, vs in st.items()}
        except yaml.YAMLError as e:
            print(f"Error loading user settings: {e}")
            return {}

# we add user settings to the global namespace
user_settings = load_settings(user_settings_path)
globals().update(user_settings)
cr_sts = load_settings(cr_settings_path)
globals().update(cr_sts)
