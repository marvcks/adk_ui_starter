import os

c16_list = ["c16_m16_cpu","c32_m64_cpu","c16_m64_cpu","c16_m128_cpu"]
cpu_description = ["设置核心数为2",]
USED_MACHINE_TYPE = c16_list[1]
MACHINE_SETTING = cpu_description[0]
# Global Configuration
BOHRIUM_EXECUTOR = {
    "type": "dispatcher",
    "machine": {
        "batch_type": "Bohrium",
        "context_type": "Bohrium",
        "remote_profile": {
            "email": os.getenv("BOHRIUM_EMAIL"),
            "password": os.getenv("BOHRIUM_PASSWORD"),
            "program_id": int(os.getenv("BOHRIUM_PROJECT_ID")),
            "input_data": {
                "image_name": "registry.dp.tech/dptech/dp/native/prod-13364/autots:0.1.0",
                "job_type": "container",
                "platform": "ali",
                "scass_type": USED_MACHINE_TYPE
                }
            }
        }
    }

BOHRIUM_STORAGE = BOHRIUM_STORAGE = {
    "type": "bohrium",
    "username": os.getenv("BOHRIUM_EMAIL"),
    "password": os.getenv("BOHRIUM_PASSWORD"),
    "project_id": int(os.getenv("BOHRIUM_PROJECT_ID"))
    }


BOHRIUM_ACCESS_KEY="a03ba3fc99c94b32afad3a94ffdcd995"
BOHRIUM_PROJECT_ID=596675
BohriumStorge = {
    "type": "https",
    "plugin": {
        "type": "bohrium",
        "access_key": BOHRIUM_ACCESS_KEY,
        "project_id": BOHRIUM_PROJECT_ID,
        "app_key": "agent"
        }
    }
BohriumExecutor = {
    "type": "dispatcher",
    "machine": {
        "batch_type": "OpenAPI",
        "context_type": "OpenAPI",
        "remote_profile": {
            "access_key": BOHRIUM_ACCESS_KEY,
            "project_id": BOHRIUM_PROJECT_ID,
            "app_key": "agent",
            "image_address": "registry.dp.tech/dptech/dp/native/prod-13364/autots:0.1.0",
            "platform": "ali",
            "machine_type": USED_MACHINE_TYPE
            }
        },
        "resources": {
            "envs": {}
        }
    }

BOHRIUM_EXECUTOR = BohriumExecutor
BOHRIUM_STORAGE = BohriumStorge