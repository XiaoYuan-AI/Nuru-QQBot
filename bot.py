from nonebot import get_driver, init, load_plugins, run
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

PLUGIN_DIR = "src/plugins"


def main() -> None:
    init()
    driver = get_driver()
    driver.register_adapter(OneBotV11Adapter)
    load_plugins(PLUGIN_DIR)
    run()


if __name__ == "__main__":
    main()
