from PyCharacterAI import Client
from PyCharacterAI.types import CharacterShort # We be initializing custom CharacterShorts with this one!!
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QTabWidget, 
                            QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox,QTextEdit,
                            QListWidget, QListWidgetItem,QComboBox,QCheckBox
                            ,QStackedWidget)
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import QTimer

import sys
import asyncio
import qasync
from qasync import QEventLoop, asyncSlot
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import aiohttp
import threading # To avoid stalling QT thread (main thread) when doing async stuff
import io
import random
from defusedxml.ElementTree import parse
from xml.etree.ElementTree import Element,SubElement, ElementTree
import requests
import json
from urllib.parse import quote

### ANON SUPPORT

def getAnonymousSearchCharsViaShittyCAIAPI(searchQuery):
    # This is a dumb reverse-engineered function. Do not judge.
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://character.ai/",
        "User-Agent": "Mozilla/5.0"
    }

    payload = {
        "0": {
            "json": {
                "searchQuery": searchQuery,
                "tagId": None,
                "sortedBy": None
            },
            "meta": {
                "values": {
                    "tagId": ["undefined"],
                    "sortedBy": ["undefined"]
                }
            }
        }
    }

    encoded_payload = quote(json.dumps(payload))
    url = f"https://character.ai/api/trpc/search.search?batch=1&input={encoded_payload}"

    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        chars = data[0]["result"]["data"]["json"].get("characters", [])
        return [CharacterShort(c) for c in chars]
    except Exception as e:
        print(f"💀 Search API exploded: {e}")
        return [] # We should honestly return an error in-ui but eh, it'll be fine for now.

def getAnonymousFeaturedCharsViaShittyCAIAPI():
    # This is a shitty API that is not even documented. We just reverse engineered it.
    # It is used by the website. I just used devtools and yanked the API from there.
    headers = {
        "Content-Type": "application/json",
        "Referer": "https://character.ai/",
        "User-Agent": "Mozilla/5.0"
    } # Known working headers. May be seen as a bot, but whatever. We will rock you!

    payload = {
        "0": {
            "json": {
                "category": "Entertainment & Gaming"
            }
        }
    }

    url = "https://character.ai/api/trpc/discovery.charactersByCuratedAnon?batch=1&input=" + requests.utils.quote(json.dumps(payload))
    # Reverse engineered, but not using PyCharacterAI as it threw a hissy fit when anonymous.
    res = requests.get(url, headers=headers)
    data = res.json()
    chars = data[0]["result"]["data"]["json"].get("characters", [])
    cshorts = []
    for char in chars:
        cshorts.append(CharacterShort(char))
    return cshorts # Converting back to CharacterShorts so we can use them in the same way as PyCharacterAI does, except we use a different API endpoint.
def getTextFromTurn(turn): # Gets a swipe's content (you can swipe to generate new reply if the bot is dumb like usual)
    primaryCandidate = turn.get_primary_candidate()
    if primaryCandidate is not None:
        return primaryCandidate
    else:
        candidates = turn.get_candidates()
        # Get random candidate
        randomCandidate = random.choice(candidates)
        return randomCandidate
# Chat messages are known as turns. Dumb for PyCharacterAI to do that, but whatever.
class CharacterAIApp(QMainWindow):


    def __init__(self):
        super().__init__()
        # Load settings from XML
        try:
            tree = parse("config/settings.xml")
            root = tree.getroot()
        except:
            # Create new settings file if it doesn't exist
            root = Element("Settings")
            appearance = SubElement(root, "Appearance")
            SubElement(appearance, "Theme", type="string", value="Default")
            SubElement(appearance, "AdditionalCSS", type="string", value="/*Additional CSS to use. Only works on the theme Default*/")
            
            auth = SubElement(root, "Auth")
            SubElement(auth, "Token", type="string", value="")
            
            other = SubElement(root, "Other") 
            SubElement(other, "CentralAuthority", type="string", value="https://ca.chattedrooms.com", description="Creative Assurance server")
            SubElement(other, "LocalCensorship", type="bool", value="False", description="Enable local censorship (via DistilBERT, but currently unavailable)")
            ai_type = SubElement(other, "AIType", type="list", description="AI server to use (only works on Custom AI compatible C.AI bots)", value="CharacterAI (do not use custom model)", id="CAI")
            SubElement(ai_type, "item", id="OAICompat").text = "OpenAI-Compatible"
            SubElement(ai_type, "item", id="ollama").text = "Ollama"
            SubElement(ai_type, "item", id="Local").text = "Local GGUF"
            SubElement(ai_type, "item", id="CAI").text = "CharacterAI (do not use custom model)"
            SubElement(other, "GPTLoc", requirement="AIType==OAICompat", type="string", value="https://api.openai.com", description="OpenAI-compatible server. Only in effect if you choose OpenAI-Compatible")
            SubElement(other, "GPTKey", requirement="AIType==OAICompat", type="string", value="sk-...", description="OpenAI-compatible server apikey. Only in effect if you choose OpenAI-Compatible")
            SubElement(other, "GPTModel", requirement="AIType==OAICompat", type="string", value="gpt-3.5-turbo", description="Model to use for OpenAI-compatible servers. Only in effect if you choose OpenAI-Compatible")
            SubElement(other, "OllamaModel", requirement="AIType==ollama", type="string", value="llama2", description="Model to use for Ollama servers. Only in effect if you choose Ollama.")
            SubElement(other, "LocalModel", requirement="AIType==Local", type="string", value="TheBloke/Mistral-7B-Instruct-v0.2-GGUF", description="HuggingFace model to use for Local GGUF mode.")
            SubElement(other, "Label1", type="label", requirement="AIType==CAI", value="No additional options available for Character.AI backend.")
            
            ElementTree(root).write("config/settings.xml")
        self.ConfigRoot = root
        self.LoadTheme(root.find(".//Appearance/Theme").get("value", "Default"))
        self.client = Client()
        self.init_login_ui()

    def LoadTheme(self,themeselected):
        if themeselected == "Default":
            # Set additional CSS from settings
            self.setStyleSheet(self.ConfigRoot.find(".//Appearance/AdditionalCSS").get("value", ""))
            return 
        self.globalStyleSheet = ""
        try:
            tree = parse("config/styles.xml")
            root = tree.getroot()
            print("Found styles.xml!", root)
            
            theme = root.find(f".//Theme[@name='{themeselected}']")
            if theme is not None:
                style = theme.find("GlobalStyle")
                if style is not None:
                    print("Found global style in theme!")
                    self.globalStyleSheet += style.text
                else:
                    print("No GlobalStyle found in theme.")
            else:
                print(f"Theme '{themeselected}' not found. Using system QT default theme.")
        except Exception as e:
            print(f"Error loading styles: {str(e)}")
        self.setStyleSheet(self.globalStyleSheet)   

    
    def init_login_ui(self,autoguest=False,autologin=True):
        # Check if token exists in config
        token_elem = self.ConfigRoot.find(".//Auth/Token")
        saved_token = token_elem.get("value", "")
        # Show login UI if no token or authentication failed
        self.setWindowTitle("Character AI Token Login")
        self.setFixedSize(480, 200)
        login_widget = QWidget()
        login_layout = QVBoxLayout()

        self.token_input = QLineEdit()
        login_button = QPushButton("Login")
        anonbutton = QPushButton("Login Anonymously (guest mode)")
        # This pretends to be a logged out browser by just not supplying a token.
        anonbutton.clicked.connect(lambda: asyncio.create_task(self.NoLogin("")))
        login_button.clicked.connect(self.handle_login)
        if autoguest:
            self.setWindowTitle("Logging in as guest...")
            # Automatically login as guest
            QTimer.singleShot(0, anonbutton.click)
            login_layout.addWidget(anonbutton)
            self.setCentralWidget(login_widget)
            return
        if saved_token and autologin:
            self.setWindowTitle("Logging in...")
            # Automatically login if token is available
            self.token_input.setText(saved_token)
            QTimer.singleShot(0, login_button.click)
            login_layout.addWidget(login_button)
            self.setCentralWidget(login_widget)
            return
        token_label = QLabel("Enter your Character AI token:\n(we can't use password login yet, we haven't reverse engineered the login flow)")
        token_label.setWordWrap(True)
        warning_label = QLabel("WARNING: Never share your token with anyone, unless this is a shared account or you want to be hacked.")
        warning_label.setWordWrap(True)

        login_layout.addWidget(token_label)
        login_layout.addWidget(warning_label)
        login_layout.addWidget(self.token_input)
        login_layout.addWidget(login_button)
        login_layout.addWidget(anonbutton)

        login_widget.setLayout(login_layout)
        self.setCentralWidget(login_widget)

    def init_main_ui(self,guest):
        self.setWindowTitle("Characterinator (Character AI Third-party Client)")
        self.setMinimumSize(300,400)
        self.setMaximumSize(9999, 9999) # Disable limitations
        self.resize(800, 600)
        self.stacked = QStackedWidget()
        self.guestMode = guest
        if guest:
            self.setWindowTitle("Characterinator (Anonymous)")

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.layout1 = QVBoxLayout()
        self.layout2 = QVBoxLayout()

        self.tab1.setLayout(self.layout1)
        self.tab2.setLayout(self.layout2)

        self.tabs.addTab(self.tab1, "Welcome")
        if not self.guestMode:
            self.tabs.addTab(self.tab2, "Chats")
        self.stacked.addWidget(self.tabs)
        self.setCentralWidget(self.stacked)
        
        # Initialize tab contents
        asyncio.create_task(self.init_welcome_tab())
        if not guest:
            asyncio.create_task(self.init_chats_tab())
        asyncio.create_task(self.init_search_tab())
        asyncio.create_task(self.init_settings_tab())

    async def init_chat_menu(self, character_id,chat_id):
        # Create a new window widget and hide the main window
        self.chat_window = QWidget()
        self.chat_window.setWindowTitle("Chat")
        self.chat_window.setGeometry(self.geometry())
        layout = QVBoxLayout()
        
        # Add back button
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: handle_back_button(self))
        layout.addWidget(back_button)
        
        messages_list = QListWidget()
        input_field = QLineEdit()
        send_button = QPushButton("Send")
        
        layout.addWidget(messages_list)
        layout.addWidget(input_field)
        layout.addWidget(send_button)
        
        self.chat_window.setLayout(layout)
        self.stacked.addWidget(self.chat_window)
        self.stacked.setCurrentWidget(self.chat_window)

        def handle_back_button(self):
            self.stacked.setCurrentWidget(self.tabs)
            self.stacked.removeWidget(self.chat_window)
            self.chat_window.deleteLater()
        # Fetch chat history
        messages = await self.client.chat.fetch_all_messages(chat_id)
        # Display messages in list
        for turn in reversed(messages): # Apparently first message is the last in the list, dumb decision by c.ai. We have to reverse it.
            item = QListWidgetItem()
            message = getTextFromTurn(turn)
            
            # Create QTextEdit for markdown rendering
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setMarkdown(message.text)
            text_edit.setWordWrapMode(True)
            text_edit.setFrameStyle(0)  # Remove frame
            text_edit.setMinimumHeight(100)
            
            # Style messages differently for bot vs user
            if turn.author_is_human:
                text_edit.setAlignment(Qt.AlignRight)
                text_edit.setStyleSheet("""
                    QTextEdit {
                    background-color: #2F4F4F;
                    border-radius: 10px;
                    padding: 8px;
                    margin: 4px 20px 4px 50px;
                    }
                """)
            else:
                text_edit.setAlignment(Qt.AlignLeft)
                text_edit.setStyleSheet("""
                    QTextEdit {
                    background-color: 	#696969;
                    border-radius: 10px;
                    padding: 8px;
                    margin: 4px 50px 4px 20px;
                    }
                """)
                
            # Add QTextEdit to list item
            messages_list.addItem(item)
            messages_list.setItemWidget(item, text_edit)
            
            # Set item size to match content
            item.setSizeHint(text_edit.sizeHint())
        messages_list.scrollToBottom()
        # Connect send button to async handler
        async def send_message():
            if input_field.text():
                try:
                    # Add user message
                    user_item = QListWidgetItem()
                    user_text = QTextEdit()
                    user_text.setReadOnly(True)
                    user_text.setMarkdown(input_field.text())
                    user_text.setWordWrapMode(True)
                    user_text.setFrameStyle(0)
                    user_text.setAlignment(Qt.AlignRight)
                    user_text.setStyleSheet("""
                    QTextEdit {
                        background-color: #2F4F4F;
                        border-radius: 10px;
                        padding: 8px;
                        margin: 4px 20px 4px 50px;
                    }
                    """)
                    messages_list.addItem(user_item)
                    messages_list.setItemWidget(user_item, user_text)
                    user_item.setSizeHint(user_text.sizeHint())

                    # Add bot response item that will be updated
                    bot_item = QListWidgetItem()
                    bot_text = QTextEdit()
                    bot_text.setReadOnly(True)
                    bot_text.setWordWrapMode(True)
                    bot_text.setFrameStyle(0)
                    bot_text.setAlignment(Qt.AlignLeft)
                    bot_text.setStyleSheet("""
                    QTextEdit {
                        background-color: #696969;
                        border-radius: 10px;
                        padding: 8px;
                        margin: 4px 50px 4px 20px;
                    }
                    """)
                    messages_list.addItem(bot_item)
                    messages_list.setItemWidget(bot_item, bot_text)
                    
                    # Start streaming response
                    response = await self.client.chat.send_message(character_id=character_id, 
                                                                   chat_id=chat_id, text=input_field.text(), streaming=True)
                    lastMessageContent = ""
                    async for message in response:
                        new_content = message.get_primary_candidate().text
                        bot_text.setMarkdown(new_content)
                        bot_item.setSizeHint(bot_text.sizeHint())
                        messages_list.scrollToBottom()
                        lastMessageContent = new_content
                        QApplication.processEvents()

                    input_field.clear()
                except Exception as e:
                    QMessageBox.critical(self.chat_window, "Error", f"Failed to send message: {str(e)}")

        send_button.clicked.connect(lambda: asyncio.create_task(send_message()))

    async def init_welcome_tab(self):
        welcome_label = QLabel(
            f"Welcome to Characterinator! These bots are what CharacterAI thinks {'should be featured' if self.guestMode else 'you might like'}."+
            f" (but you prolly won't{' agree' if self.guestMode else ''}).")
        # It makes sense for the text tho. Reason: You have phases where you like certain characters, and then you get bored of them. So the bots are recommended based on your chat history.
        # But the featured ones are just random bots that are popular and ended up in the entertainment category.
        # For guests, we can't use recommendations due to not being accurate, so we just use the featured ones.
        welcome_label.setWordWrap(True)
        self.layout1.addWidget(welcome_label)
        
        loading_label = QLabel(f"Loading {'featured' if self.guestMode else 'recommended'} characters...")
        self.layout1.addWidget(loading_label)
        
        try:
            # Create list widget for recommended characters
            self.rec_list = QListWidget()
            self.layout1.addWidget(self.rec_list)
            
            # Start loading characters in background
            asyncio.create_task(self.load_recommended_characters(loading_label))
            
        except Exception as e:
            loading_label.deleteLater()
            error_label = QLabel(f"Error initializing {'featured' if self.guestMode else 'recommended'} characters: {str(e)}")
            self.layout1.addWidget(error_label)

    async def load_recommended_characters(self, loading_label):
        try:
            if self.guestMode:
                characters = getAnonymousFeaturedCharsViaShittyCAIAPI() # Hah! No async?
            else:
                characters = await self.client.character.fetch_recommended_characters()
            
            async with aiohttp.ClientSession() as session:
                for character in characters:
                    # Create widget for each character
                    item_widget = QWidget()
                    item_layout = QVBoxLayout()
                    
                    # Add name and title 
                    name_label = QLabel(f"{character.name}")
                    title_label = QLabel(f"{character.title}")
                    item_layout.addWidget(name_label)
                    item_layout.addWidget(title_label)
                    
                    # Add avatar
                    avatar_url = character.avatar.get_url(size=200) if character.avatar else "https://cdn3.emoji.gg/emojis/5708-rickroll-static.png"
                    try:
                        async with session.get(avatar_url) as response:
                            image_data = await response.read()
                            pixmap = QPixmap()
                            pixmap.loadFromData(image_data)
                            avatar_label = QLabel()
                            avatar_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            item_layout.addWidget(avatar_label)
                    except Exception:
                        avatar_label = QLabel("X")
                        item_layout.addWidget(avatar_label)
                    
                    item_widget.setLayout(item_layout)
                    
                    # Add to list
                    list_item = QListWidgetItem()
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.rec_list.addItem(list_item)
                    self.rec_list.setItemWidget(list_item, item_widget)
            
            loading_label.deleteLater()
        except Exception as e:
            loading_label.deleteLater()
            error_label = QLabel(f"Error loading recommended characters: {str(e)}")
            self.layout1.addWidget(error_label)

    async def init_chats_tab(self):
        loading_label = QLabel("Loading chats...")
        self.layout2.addWidget(loading_label)
        
        # Create list widget
        self.chat_list = QListWidget()
        
        try:
            await self.update_chats_list(loading_label)
            self.layout2.addWidget(self.chat_list)
        except Exception as e:
            loading_label.deleteLater()
            error_label = QLabel(f"Error loading chats: {str(e)}")
            self.layout2.addWidget(error_label)

    async def update_chats_list(self, loading_label=None):
        try:
            chats = await self.client.chat.fetch_recent_chats()
            
            self.chat_list.clear()
            async with aiohttp.ClientSession() as session:
                for chat in chats:
                    item_widget = QWidget()
                    item_layout = QVBoxLayout()
                    
                    name_label = QLabel(f"Character: {chat.character_name}")
                    item_layout.addWidget(name_label)
                    
                    avatar_url = chat.character_avatar.get_url(size=200) if chat.character_avatar else "https://cdn3.emoji.gg/emojis/5708-rickroll-static.png"
                    try:
                        async with session.get(avatar_url) as response:
                            image_data = await response.read()
                            pixmap = QPixmap()
                            pixmap.loadFromData(image_data)
                            avatar_label = QLabel()
                            avatar_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            item_layout.addWidget(avatar_label)
                    except Exception:
                        avatar_label = QLabel("X")
                        item_layout.addWidget(avatar_label)
                    
                    open_chat_btn = QPushButton("Open Chat")
                    item_layout.addWidget(open_chat_btn)
                    open_chat_btn.clicked.connect(lambda _, character_id=chat.character_id, chat_id=chat.chat_id: asyncio.create_task(self.init_chat_menu(character_id, chat_id)))
                    
                    item_widget.setLayout(item_layout)
                    
                    list_item = QListWidgetItem()
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.chat_list.addItem(list_item)
                    self.chat_list.setItemWidget(list_item, item_widget)

            if loading_label:
                loading_label.deleteLater()
        except Exception as e:
            raise e
    
    async def init_search_tab(self):
        search_widget = QWidget()
        search_layout = QVBoxLayout()
        
        search_input = QLineEdit()
        search_button = QPushButton("Search")
        results_list = QListWidget()
        
        search_layout.addWidget(QLabel("Search for characters:"))
        search_layout.addWidget(search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(results_list)
        
        search_widget.setLayout(search_layout)
        
        self.tabs.addTab(search_widget, "Search")
        
        async def perform_search():
            query = search_input.text()
            if not query:
                return
                
            results_list.clear()
            try:
                if self.guestMode:
                    characters = getAnonymousSearchCharsViaShittyCAIAPI(query)
                else:
                    characters = await self.client.character.search_characters(query)
                
                async with aiohttp.ClientSession() as session:
                    for character in characters:
                        item_widget = QWidget()
                        item_layout = QVBoxLayout()
                        
                        name_label = QLabel(character.name)
                        title_label = QLabel(character.title)
                        item_layout.addWidget(name_label)
                        item_layout.addWidget(title_label)
                        
                        avatar_url = character.avatar.get_url(size=200) if character.avatar else "https://cdn3.emoji.gg/emojis/5708-rickroll-static.png"
                        try:
                            async with session.get(avatar_url) as response:
                                image_data = await response.read()
                                pixmap = QPixmap()
                                pixmap.loadFromData(image_data)
                                avatar_label = QLabel()
                                avatar_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                                item_layout.addWidget(avatar_label)
                        except Exception:
                            avatar_label = QLabel("X")
                            item_layout.addWidget(avatar_label)
                        
                        item_widget.setLayout(item_layout)
                        
                        list_item = QListWidgetItem()
                        list_item.setSizeHint(item_widget.sizeHint())
                        results_list.addItem(list_item)
                        results_list.setItemWidget(list_item, item_widget)
                        
            except Exception as e:
                error_item = QListWidgetItem(f"Search failed: {str(e)}")
                results_list.addItem(error_item)

        search_button.clicked.connect(lambda: asyncio.create_task(perform_search()))


    async def init_settings_tab(self):
        root = self.ConfigRoot
        settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        
        # Create tab widget
        settings_tabs = QTabWidget()
        
        # Create tabs
        appearance_tab = QWidget()
        account_tab = QWidget()
        other_tab = QWidget()
        
        appearance_layout = QVBoxLayout()
        account_layout = QVBoxLayout()
        other_layout = QVBoxLayout()

        # Theme selection in appearance tab
        theme_label = QLabel("Theme:")
        appearance_layout.addWidget(theme_label)
        
        theme_dropdown = QComboBox()
        try:
            styles_tree = parse("config/styles.xml")
            styles_root = styles_tree.getroot()
            themes = styles_root.findall(".//Theme")
            for theme in themes:
                name = theme.get("name")
                if name:
                    theme_dropdown.addItem(name)
            
            # Set current theme from settings
            current_theme = root.find(".//Appearance/Theme").get("value", "Default")
            index = theme_dropdown.findText(current_theme)
            if index >= 0:
                theme_dropdown.setCurrentIndex(index)
        except Exception as e:
            print(f"Error loading themes: {str(e)}")
            
        def save_theme(theme_name):
            self.LoadTheme(theme_name)
            theme_elem = root.find(".//Appearance/Theme")
            theme_elem.set("value", theme_name)
            ElementTree(root).write("config/settings.xml")
            # Refresh visibility of requirement-dependent widgets
            refresh_requirements()
            
        theme_dropdown.currentTextChanged.connect(save_theme)
        

        appearance_layout.addWidget(theme_dropdown)
        appearance_layout.addStretch()
        appearance_tab.setLayout(appearance_layout)
        
        # Additional CSS editor
        css_label = QLabel("Additional CSS:")
        appearance_layout.addWidget(css_label)
        
        css_editor = QTextEdit()
        css_editor.setPlainText(root.find(".//Appearance/AdditionalCSS").get("value", ""))
        appearance_layout.addWidget(css_editor)
        
        def save_css():
            css_value = css_editor.toPlainText()
            root.find(".//Appearance/AdditionalCSS").set("value", css_value)
            ElementTree(root).write("config/settings.xml")
            self.LoadTheme(root.find(".//Appearance/Theme").get("value", "Default"))
        css_editor.textChanged.connect(save_css)
        # Account info in account tab
        account_info_label = QLabel("Account Information:")
        account_layout.addWidget(account_info_label)
        
        try:
            if self.guestMode:
                username_label = QLabel("Username: Guest")
            else:
                user = await self.client.account.fetch_me()
                username_label = QLabel(f"Username: {user.username}")
            account_layout.addWidget(username_label)
        except Exception as e:
            error_label = QLabel(f"Failed to load user info: {str(e)}")
            account_layout.addWidget(error_label)
        
        if self.guestMode:
            logout_button = QPushButton("Return to Login")
            logout_button.clicked.connect(lambda: self.handle_logout(False))
            account_layout.addWidget(logout_button)
        else:
            logout_button = QPushButton("Logout")
            logout_button.clicked.connect(lambda: self.handle_logout(False))
            logoutanon_button = QPushButton("Relog As Anonymous")
            logoutanon_button.clicked.connect(lambda: self.handle_logout(True))
            account_layout.addWidget(logout_button)
            account_layout.addWidget(logoutanon_button)
        account_layout.addStretch()
        account_tab.setLayout(account_layout)

        # Store widgets that have requirements
        requirement_widgets = []

        # Other settings tab
        other_settings = root.findall(".//Other/*")
        for setting in other_settings:
            setting_type = setting.get("type")
            setting_value = setting.get("value")
            setting_desc = setting.get("description", "")
            setting_req = setting.get("requirement", "")
            
            label = QLabel(f"{setting.tag}:")
            desc_label = None
            if setting_desc:
                desc_label = QLabel(setting_desc)
                desc_label.setStyleSheet("color: gray; font-size: 10px;")
                other_layout.addWidget(desc_label)
            
            if setting_type == "int":
                input_widget = QLineEdit(setting_value)
                input_widget.setValidator(QIntValidator())
            elif setting_type == "float":
                input_widget = QLineEdit(setting_value)
                input_widget.setValidator(QDoubleValidator())
            elif setting_type == "bool":
                input_widget = QCheckBox()
                input_widget.setChecked(setting_value.lower() == "true")
            elif setting_type == "list":
                input_widget = QComboBox()
                for item in setting.findall("item"):
                    item_value = item.text
                    item_id = item.get("id", item_value)
                    input_widget.addItem(item_value, item_id)
                input_widget.setCurrentText(setting_value)
            elif setting_type == "label":
                input_widget = QLabel(setting_value)
                other_layout.addWidget(input_widget)
            else:
                input_widget = QLineEdit(setting_value)

            # If this setting has a requirement, store it and hide widgets initially 
            if setting_req:
                requirement_widgets.append((label, input_widget, setting_req))
                if desc_label:
                    requirement_widgets.append((desc_label, desc_label, setting_req))
            if setting_type == "label":
                label.deleteLater() # Don't show unnecessary label for label type settings (because they're already)
                other_layout.addWidget(input_widget)
                continue
            
            def make_save_fn(elem, widget):
                def save_fn():
                    if isinstance(widget, QCheckBox):
                        elem.set("value", str(widget.isChecked()))
                    elif isinstance(widget, QComboBox):
                        elem.set("value", widget.currentText())
                        elem.set("id", widget.currentData())
                    else:
                        elem.set("value", widget.text())
                    ElementTree(root).write("config/settings.xml")
                    refresh_requirements()
                return save_fn
            
            if isinstance(input_widget, QCheckBox):
                input_widget.stateChanged.connect(make_save_fn(setting, input_widget))
            elif isinstance(input_widget, QComboBox):
                input_widget.currentTextChanged.connect(make_save_fn(setting, input_widget))
            else:
                input_widget.editingFinished.connect(make_save_fn(setting, input_widget))
            
            other_layout.addWidget(label)
            other_layout.addWidget(input_widget)

        def refresh_requirements():
            for label, widget, req in requirement_widgets:
                if "==" in req:
                    list_name, required_id = req.split("==")
                    list_elem = root.find(f".//{list_name}")
                    show = list_elem is not None and list_elem.get("id") == required_id
                elif "!=" in req:
                    list_name, required_id = req.split("!=")
                    list_elem = root.find(f".//{list_name}")
                    show = list_elem is not None and list_elem.get("id") != required_id
                else:
                    show = True
                try:
                    label.setVisible(show)
                except:
                    pass # This is normal for non-label "settings" like Label type
                widget.setVisible(show)
            
        # Initial refresh of requirements
        refresh_requirements()
            
        other_layout.addStretch()
        other_tab.setLayout(other_layout)
        
        # Add tabs to tab widget
        settings_tabs.addTab(appearance_tab, "Appearance")
        settings_tabs.addTab(account_tab, "Account") 
        settings_tabs.addTab(other_tab, "Other")
        
        # Add tab widget to main layout
        settings_layout.addWidget(settings_tabs)
        
        settings_widget.setLayout(settings_layout)
        self.tabs.addTab(settings_widget, "Settings")

    def handle_logout(self,guest):
        self.client = Client()
        self.init_login_ui(autoguest=guest,autologin=False)
        # Remove token from config
        token_elem = self.ConfigRoot.find(".//Auth/Token")
        token_elem.set("value", "")
        ElementTree(self.ConfigRoot).write("config/settings.xml")

    

    @asyncSlot()
    async def handle_login(self):
        token = self.token_input.text()
        if not token:
            QMessageBox.warning(self, "Error", "Please enter a token")
            return

        try:
            await self.client.authenticate(token)
            self.init_main_ui(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication failed: {str(e)}")
    
    async def loginViaToken(self, token):
        try:
            await self.client.authenticate(token)
            self.init_main_ui(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication failed: {str(e)}")

    async def NoLogin(self, token):
        try:
            self.init_main_ui(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication failed: {str(e)}")


async def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = CharacterAIApp()
    window.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        sys.exit(0)

# CharacterAI sucks normally! We improve it by making a third-party client that is better than the official one.
# They have such an incompetent team that they can't even make a good client. So we made one for them.
# This is a third-party client for Character AI. We are not affiliated with Character AI in any way. 
# (but we are a competitor since we make our own platform as the main project, this is just a side project)
# We are not responsible for any bans or issues that may arise from using this client.
# Built by people who actually use the platform. You're welcome.
# We should stop rickrolling people with the fallback though, even if it is funny.