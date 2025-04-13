from PyCharacterAI import Client
from PyQt5.QtWidgets import (QApplication, QLabel, QMainWindow, QTabWidget, 
                            QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox,QTextEdit,
                            QListWidget, QListWidgetItem)
import sys
import asyncio
import qasync
from qasync import QEventLoop, asyncSlot
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import aiohttp
import io
import random

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
        self.client = Client()
        self.init_login_ui()
        
    def init_login_ui(self):
        self.setWindowTitle("Character AI Token Login")
        self.setFixedSize(480, 125)

        login_widget = QWidget()
        login_layout = QVBoxLayout()

        self.token_input = QLineEdit()
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.handle_login)

        login_layout.addWidget(QLabel("Enter your Character AI token:\n(we can't use password login yet, we haven't reverse engineered the login flow)"))
        login_layout.addWidget(self.token_input)
        login_layout.addWidget(login_button)

        login_widget.setLayout(login_layout)
        self.setCentralWidget(login_widget)

    def init_main_ui(self):
        self.setWindowTitle("Characterinator (Character AI Third-party Client)")
        self.setFixedSize(600, 400)

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.layout1 = QVBoxLayout()
        self.layout2 = QVBoxLayout()

        self.tab1.setLayout(self.layout1)
        self.tab2.setLayout(self.layout2)

        self.tabs.addTab(self.tab1, "Welcome")
        self.tabs.addTab(self.tab2, "Chats")

        self.setCentralWidget(self.tabs)
        
        # Initialize tab contents
        asyncio.create_task(self.init_welcome_tab())
        asyncio.create_task(self.init_chats_tab())

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
        self.hide()
        self.chat_window.show()

        def handle_back_button(self):
            self.chat_window.close()
            self.show()
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
        welcome_label = QLabel("Welcome to Characterinator! These bots are what CharacterAI thinks you might like. (but you prolly won't)")
        # It makes sense for the text tho. Reason: You have phases where you like certain characters, and then you get bored of them. So the bots are recommended based on your chat history.
        welcome_label.setWordWrap(True)
        self.layout1.addWidget(welcome_label)
        
        loading_label = QLabel("Loading recommended characters...")
        self.layout1.addWidget(loading_label)
        
        try:
            characters = await self.client.character.fetch_recommended_characters()
            
            # Create list widget for recommended characters
            self.rec_list = QListWidget()
            
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
            
            self.layout1.addWidget(self.rec_list)
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
            chats = await self.client.chat.fetch_recent_chats()
            
            async with aiohttp.ClientSession() as session:
                for chat in chats:
                    # Create custom widget for list item
                    item_widget = QWidget()
                    item_layout = QVBoxLayout()
                    
                    # Name label
                    name_label = QLabel(f"Character: {chat.character_name}")
                    item_layout.addWidget(name_label)
                    
                    # Avatar image
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
                    
                    # Open chat button
                    open_chat_btn = QPushButton("Open Chat")
                    item_layout.addWidget(open_chat_btn)
                    open_chat_btn.clicked.connect(lambda _, character_id=chat.character_id, chat_id=chat.chat_id: asyncio.create_task(self.init_chat_menu(character_id, chat_id)))
                    
                    item_widget.setLayout(item_layout)
                    
                    # Add to list
                    list_item = QListWidgetItem()
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.chat_list.addItem(list_item)
                    self.chat_list.setItemWidget(list_item, item_widget)
            
            self.layout2.addWidget(self.chat_list)
            loading_label.deleteLater()
        except Exception as e:
            loading_label.deleteLater()
            error_label = QLabel(f"Error loading chats: {str(e)}")
            self.layout2.addWidget(error_label)

    @asyncSlot()
    async def handle_login(self):
        token = self.token_input.text()
        if not token:
            QMessageBox.warning(self, "Error", "Please enter a token")
            return

        try:
            await self.client.authenticate(token)
            self.init_main_ui()
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
