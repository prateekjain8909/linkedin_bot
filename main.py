import time
from selenium import webdriver
import utils
import config
from companies import companies


class SeleniumDriver:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SeleniumDriver, cls).__new__(cls, *args, **kwargs)
            cls._instance.driver = webdriver.Chrome()
        return cls._instance

    def get_driver(self):
        return self.driver

    def close(self):
        self.driver.quit()


def main():
    # Create a logger instance
    utils.set_logger()
    driver = SeleniumDriver().get_driver()
    utils.login(driver, config.login_cookie_path, config.login_username, config.login_password)
    utils.process_companies(driver, companies)


if __name__ == "__main__":
    main()
