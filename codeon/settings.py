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
cr_id_regex = r"cr_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})_"
to_dt = lambda ts: dt.strptime(ts, "%Y-%m-%d-%H-%M-%S")

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
# cr_headers
pg_header_regex = r"(#--- cr_op:.*?---#)"
unit_header_regex = r"(#-- cr_op:.*?--#)(.*?)(?=#--|$)"
md_fence_regex = r"^\s*```[a-zA-Z]*\n|(\n\s*```\s*$)"
# the following directories refer to the temporary package structure and logs
# the resulting paths depend on the work_path or cwd this package is run inside
# all process files are stored here
integration_formats = {
    'md': '__cr_integration_file__',
    'json': '__cr_integration_json__',
}

phases = ('cr_json', 'cr_integration', 'cr_processing')# cr_finalizing

cr_integration_file_templ_path = os.path.join(resources_dir, 'cr_integration_file_template.py')
cq_ex_llm_file = os.path.join(resources_dir, 'CQ-EX-LLM.md')
temp_dir = lambda pg_name: os.path.join(resources_dir, 'cr_logs', pg_name)
# do not change order here
# all cr_prompt files are stored here
cr_prompt_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_prompts')
cr_prompt_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.md'
# all cr_json_files are staged here
cr_jsons_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_jsons')
cr_json_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split('.')[0]}.json'
# all cr_integration_files are staged here
cr_integration_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_integrations')
cr_integration_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split('.')[0]}.py'
# staging dir for source update files
cr_stages_dir = lambda pg_name: os.path.join(temp_dir(pg_name), 'cr_processing')
cr_stage_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'
# restoring overwritten source files is done from here
cr_restores_dir = lambda pg_name: os.path.join(temp_dir(pg_name), f'{pg_name}_archive')
cr_restore_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'
# all cr meta data is logged here
cr_logs_dir = lambda pg_name: os.path.join(temp_dir(pg_name), f'cr_logs')
cr_log_file_name = lambda f_name, cr_id: f'cr_{cr_id}_{f_name.split(".")[0]}.py'

cr_paths = {
    'cr_prompt_path': (cr_prompt_dir, cr_prompt_file_name),
    'cr_json_path': (cr_jsons_dir, cr_json_file_name),
    'cr_integration_path': (cr_integration_dir, cr_integration_file_name),
    'cr_processing_path': (cr_stages_dir, cr_stage_file_name),
    'cr_restore_path': (cr_restores_dir, cr_restore_file_name),
    'cr_log_path': (cr_logs_dir, cr_log_file_name),
}

file_exists_default = 'NEW'
rm_cr_prefix = lambda file_name, cr_id: file_name.replace(f'cr_{cr_id}_', '')

json_target, json_content = 'target', 'code'
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
