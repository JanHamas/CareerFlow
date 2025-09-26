import urllib.parse
import traceback, os, shutil, csv
from dotenv import load_dotenv
from playwright.async_api import Page
import google.generativeai as genai
import asyncio, random
import platform, subprocess, ctypes
from email.message import EmailMessage
import mimetypes
from config import config_input
from groq import Groq
import logging
from utils import helper
import pytest
import tempfile
from unittest.mock import patch, AsyncMock


# Make a temp_directory of pytest.fixture with decolater @pytest.fixture
@pytest.fixture
def temp_directory():
    """ Create a temporary directroy for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)

# Check CSV files creation
def test_csv_creation_in_temp_dir(temp_directory):
    """ Test CSV file creation in temporary directroy. """
    file_names = ["test.csv", "data.csv"]

    helper.create_csv_files(file_names)
    assert os.path.exists("output")
    for name in file_names:
        assert os.path.exists(os.path.join("output", name))

# Check files are accessible or not
def test_csv_files_are_accessible(temp_directory):
    """ Test that created files are accessible and writeable. """
    file_names = ["writable.csv"]
    helper.create_csv_files(file_names)
    file_path = os.path.join("output", "writable.csv")

    # Test writing to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("Test content")
    
    # Test reading from the file
    with open(file_path, 'r', encoding='utf-8') as f:
        assert f.read() == 'Test content'

# Check to load all id from processed_jobs.txt saved jobs urls
# first create a fixture
@pytest.fixture
def temp_file_with_urls():
    """ Create a temporary file with job URLs and return it's path. """
    urls = [
        "https://www.indeed.com/viewjob?jk=12345",
        "https://www.indeed.com/viewjob?jk=67890",
        "https://www.indeed.com/viewjob?jk=12345",  # duplicate
        "https://www.indeed.com/viewjob?jk=11111",
    ]
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(urls))
    yield path
    os.remove(path) # Cleanup
def test_load_processed_jobs_id(temp_file_with_urls):
    jobs = helper.load_processed_jobs_id(temp_file_with_urls)
    # Expect 3 unique jobs IDs
    assert jobs == {"12345", "67890", "11111"}

# Check the debugs screenshot folder are creating or not
@pytest.fixture
def temp_folder(tmp_path):
    return str(tmp_path / "debug_screenshots")
def test_create_folder_when_not_exists(temp_folder):
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)

    helper.create_debugging_screenshots_folder(temp_folder)

    assert os.path.exists(temp_folder)
    assert os.path.isdir(temp_folder)
def test_recreate_existing_folder(temp_folder):
    # Create folder with dummy file inside
    os.makedirs(temp_folder)
    with open(os.path.join(temp_folder, "dummy.txt"), "w") as f:
        f.write("test")

    # Call function (should remove old folder and recreate empty one)
    helper.create_debugging_screenshots_folder(temp_folder)

    assert os.path.exists(temp_folder)
    assert os.path.isdir(temp_folder)
    assert not os.listdir(temp_folder)  # folder should be empty

# Test the get jobs id function
def test_get_job_id_valid_url():
    url = "https://www.indeed.com/jobs?q=python+developer&l=remote&jk=1234567890abcdef"
    job_id = asyncio.run(helper.get_job_id(url))
    assert job_id == "1234567890abcdef"

# Check the update_processed_jobs function work mean is the new processed jobs linke updating to processed to processed or not
def test_update_processed_jobs_links(tmp_path, monkeypatch):
    # Create a temporary file path
    test_file = tmp_path / "processed_jobs.txt"

    # Patch the config so your function writes to this file instead of the real one
    monkeypatch.setattr(helper.config_input, "PROCESSED_JOBS_FILE_PATH", str(test_file))

    # Run the async function using asyncio.run
    links = ["https://job1.com", "https://job2.com"]
    asyncio.run(helper.update_processed_jobs_links(links))

    # Read back the file to check
    with open(test_file, "r") as f:
        contents = f.read().splitlines()

    assert contents == links

# Check the response of integrated ai model it's working or not
# And we are goona make a fake system to check, why we not using the real one function due to below some of problems.
"""
1, Pytest excuting very fast in milliseconds and api request are taking time so therefore we will be countring an issue even if our software work will.
2, CI/CD pipelines(like GitHub Actions) may not allow secrets or external API calls easily.
"""
class DummyResponse:
    def __init__(self, text):
        self.text = text

class DummyModel:
    def __init__(self, version):
        self.version = version
    
    def generate_content(self, prompt):
        return DummyResponse("88% match") # i'ts a fake response
    
def test_get_match_percentages(monkeypatch):
    # Monkeypatch the GenerativeModel
    monkeypatch.setattr(helper.genai, "GenerativeModel", DummyModel)

    # Run async function in sync test using asyncio.run
    result = asyncio.run(helper.get_match_percentages_from_gemini("Test prompt"))

    # Assert the fake response is returned correctly
    assert result == "88% match"

# The below test function are testing the function of human like behavior on browser page
class DummyMouse:
    async def wheel(self, x, y):
        self.wheel_called = (x, y)

    async def move(self, x, y, steps):
        self.move_called = (x, y, steps)

class DummyPage:
    def __init__(self):
        self.mouse = DummyMouse()
        self.evaluate_called = None

    async def evaluate(self, script):
        self.evaluate_called = script

def test_simulate_human_behavior(monkeypatch):
    page = DummyPage()

    # Monkeypatch random so test is predictable
    monkeypatch.setattr("random.uniform", lambda a, b: 0.1)   # always 0.1
    monkeypatch.setattr("random.randint", lambda a, b: a)     # always the min value

    # Run async function in sync test
    asyncio.run(helper.simulate_human_behavior(page))

    # Assertions: check that methods were called
    assert page.mouse.wheel_called == (0, 50)       # since randint returns min=50
    assert page.mouse.move_called == (0, 0, 2)      # since randint returns min=0 and steps=2
    assert page.evaluate_called == "window.scrollTo(0, document.body.scrollHeight)"

@pytest.mark.asyncio
async def test_wait_until_internet_is_back_with_mocks():
    # Create mock page
    mock_page = AsyncMock()
    
    # Mock check_internet to return False twice, then True
    with patch('helper.check_internet') as mock_check:
        mock_check.side_effect = [False, False, True]
        
        await helper.wait_until_internet_is_back(mock_page)
        
        # Verify check_internet was called 3 times
        assert mock_check.call_count == 3
        # Verify page.reload was called once
        mock_page.reload.assert_called_once()
