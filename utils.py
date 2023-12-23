import logging
import pickle
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Initialize the logger
def set_logger():
    global logger
    logger = logging.getLogger("linkedin_bot")
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("linkedin_bot.txt")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def process_companies(driver, companies):
    for company in companies:
        search_company_pattern = company.replace(" ", "%20")
        remaining_connections = send_connection_request_from_search_results(driver, search_company_pattern)
        send_connection_request_to_remaining_users(driver, remaining_connections)
        logger.info(f"Successfully sent connection request for {company} company")



# Load login message note from a file
def load_message_note():
    try:
        with open("invitation_note.txt", 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""


# Log in to LinkedIn and save session cookies
def login(driver, login_cookie_path, username, password):
    driver.get("https://web.whatsapp.com/")

    try:
        with open(login_cookie_path, "rb") as cookie_file:
            cookies = pickle.load(cookie_file)
            for cookie in cookies:
                driver.add_cookie(cookie)
    except FileNotFoundError:
        pass

    if not driver.get_cookies():
        driver.get("https://web.whatsapp.com/")
        username_input = driver.find_element(By.ID, "username")
        username_input.send_keys(username)

        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        with open(login_cookie_path, "wb") as cookie_file:
            pickle.dump(driver.get_cookies(), cookie_file)


def send_connection_requests_for_company(driver, company, network_type):
    if network_type not in ("S", "O"):
        raise ValueError("Invalid network_type. Use 'S' for second connections or 'O' for third connections.")

    url = (f'https://www.linkedin.com/search/results/people/?keywords={company}'
           f'&network=%5B%22{network_type}%22%5D&origin=FACETED_SEARCH&sid=OqM')

    driver.get(url)
    element_name = "div.entity-result__actions entity-result__divider"
    wait_for_element_by_css(driver, element_name)
    items = get_connections_details_from_search_results(driver)
    results = get_connections_button_mapping(items)
    direct_connection_request, remaining = filter_new_direct_connections(results)
    send_direct_connection_requests(driver, direct_connection_request)
    return remaining


def send_connection_request_from_search_results(driver, company):
    remaining_users = []
    remaining_second_connections = send_connection_requests_for_company(driver, company, "S")
    remaining_users.extend(remaining_second_connections)
    remaining_third_connections = send_connection_requests_for_company(driver, company, "O")
    remaining_users.extend(remaining_third_connections)
    return remaining_users


def send_connection_request_to_remaining_users(driver, remaining_connections):
    for remaining_connection in remaining_connections:
        try:
            send_connection_request_via_profile(remaining_connection, driver)
        except Exception:
            pass

# Wait for an element by CSS selector
def wait_for_element_by_css(driver, css_selector):
    try:
        wait = WebDriverWait(driver, 4)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_selector)))
    except TimeoutException:
        logger.error("Timed out waiting for elements to be present.")


# Get details of connections from search results
def get_connections_details_from_search_results(driver):
    return get_all_tags_by_class_name(driver, "div", "entity-result__item")


# Get all tags by class name
def get_all_tags_by_class_name(driver, tag_name, class_name):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all(tag_name, class_=class_name)
    return items


# Get all tags by class name (for a single tag)
def get_tag_by_class_name(driver, tag_name, class_name):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find(tag_name, class_=class_name)
    return items


# Map connection buttons
def get_connections_button_mapping(items):
    results = []
    for item in items:
        anchor = item.find('a', class_='app-aware-link')
        button = item.find('button')
        if anchor and button:
            href = anchor.get("href")
            button_id = button.get("id")
            button_type = button.text.strip()
            result = {
                "connection_profile": href,
                "button_id": button_id,
                "button_type": button_type
            }
            results.append(result)
    return results


# Filter new direct connections
def filter_new_direct_connections(results):
    direct_connection_request = []
    remaining = []
    for result in results:
        if result['button_type'] == "Connect":
            direct_connection_request.append(result)
        else:
            remaining.append(result['connection_profile'])
    return direct_connection_request, remaining


# Send a connection request
def send_connection_request(driver):
    try:
        aria_label = "Add a note"
        add_note_button = driver.find_element(By.XPATH, f"//button[@aria-label='{aria_label}']")
        add_note_button.click()

        textarea_name = "message"
        textarea = driver.find_element(By.NAME, textarea_name)

        message_to_paste = load_message_note()
        textarea.send_keys(message_to_paste)

        send_button_label = "Send now"
        send_button = driver.find_element(By.XPATH, f"//button[@aria-label='{send_button_label}']")
        dismiss_button = driver.find_element(By.XPATH, f"//button[@aria-label='Dismiss']")

        if send_button.is_enabled():
            send_button.click()
        else:
            dismiss_button.click()
    except Exception:
        pass


# Send connection requests
def send_direct_connection_requests(driver, direct_connections):
    for direct_connection in direct_connections:
        try:
            button = driver.find_element(By.ID, direct_connection['button_id'])
            button.click()
            send_connection_request(driver)
        except Exception:
            pass


# Get the ID of the "Invite" button
def get_invite_div(divs):
    for div in divs:
        if "Invite" in div.get("aria-label", ""):
            return div.get("id")


# Send connection request via a user's profile
def send_connection_request_via_profile(url, driver):
    driver.get(url)
    wait_for_element_by_css(driver, "pvs-profile-actions")
    div_tag = get_tag_by_class_name(driver, "div", "pvs-profile-actions")
    buttons = div_tag.find_all("button")
    div_with_role_button = div_tag.find_all("div", {'role': 'button'})
    invite_div_id = get_invite_div(div_with_role_button)
    more_button_id = ""

    for button in buttons:
        if button.text.strip() == "More":
            more_button_id = button.get("id")
        elif button.text.strip() == "Pending":
            print("The connection request has already been sent.")
            return

    wait = WebDriverWait(driver, 10)
    button = wait.until(EC.element_to_be_clickable((By.ID, more_button_id)))
    button.click()

    if invite_div_id:
        button = wait.until(EC.element_to_be_clickable((By.ID, invite_div_id)))
        button.click()

    send_connection_request(driver)
