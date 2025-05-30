# Prevent Pylance from complaining about pluginAPI not being defined (it is injected by the plugin system and not defined here)
if True == False:  # This line is just to prevent Pylance from complaining about pluginAPI not being defined
    pluginAPI = None

from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QMessageBox, QTextEdit, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QStackedWidget, QMenu, QScrollArea,
    QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtGui import QTextOption
import requests
from PySide6.QtGui import QDesktopServices, QCursor
import os
import json
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QPainter, QPainterPath  # Ensure these are imported

tab = pluginAPI.CreatePluginTab("Feed Viewer")

def getFeedURL(topic="gLj1MBqU6AgCuf4IwUE-5q4Vz-CKMP5be23HERh0Ekg", page=1, posts_to_load=5, sort="top"):
    return f"https://plus.character.ai/chat/posts/?topic={topic}&page={page}&posts_to_load={posts_to_load}&sort={sort}"

def createPost(topic="gLj1MBqU6AgCuf4IwUE-5q4Vz-CKMP5be23HERh0Ekg", title="Test Post", content="This is a test post."):
    url = "https://plus.character.ai/chat/post/create/"
    data = {
        "topic_external_id": topic,
        "post_title": title,
        "post_text": content,
        "image_rel_path": None
    }
    response = pluginAPI.postWithAuthorization(url, data)
    return response["post"]["external_id"]

class FeedViewer(QWidget):
    def __init__(self, parent=None,kurwaParent=None):
        super().__init__(parent)
        self.setObjectName("FeedViewer")
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        # Warning label
        self.warningLabel = QLabel("This feature might stop working at any time as it is from a removed part of Character AI.")
        self.warningLabel.setStyleSheet("color: red; font-weight: bold;")
        self.layout.addWidget(self.warningLabel)
        self.shouldArchivePosts = pluginAPI.pluginMetadata.get("shouldArchivePosts", False)
        if self.shouldArchivePosts: # Show green text if archiving is enabled (say that it saves post data to json)
            self.archiveLabel = QLabel("Archiving is enabled. Post data will be saved to a JSON file. Thanks to you for contributing to archiving Character AI posts!")
            self.archiveLabel.setStyleSheet("color: green; font-weight: bold;")
            self.archiveLabel.setToolTip("All post data will be saved to `feedViewerArchive/`. This includes full content, metadata, and any loaded post details.")

            self.layout.addWidget(self.archiveLabel)
            if not os.path.isdir("feedViewerArchive"):
                os.mkdir("feedViewerArchive")
        # Create Post button
        self.createPostButton = QPushButton("Create Post (probably broken)")
        self.createPostButton.setObjectName("CreatePostButton")
        self.createPostButton.setToolTip("This feature is probably broken, since the original frontend was shut down. The API endpoint was found from reversing the original frontend, but it is not guaranteed to work.")
        self.createPostButton.setEnabled(not pluginAPI.is_anonymous())  # Disable if in guest mode
        self.createPostButton.clicked.connect(lambda: self.createAPost())
        if pluginAPI.is_anonymous():
            self.createPostButton.setToolTip("You must be logged in to create a post.")
        self.layout.addWidget(self.createPostButton)
        # Feed list
        self.feedList = QListWidget()
        self.feedList.setObjectName("FeedList")
        self.feedList.setSelectionMode(QListWidget.SingleSelection)
        self.layout.addWidget(self.feedList)
        # Initialize current page and connect signals
        self.page = 1
        self.feedList.verticalScrollBar().valueChanged.connect(self.checkScroll)
        self.feedList.itemClicked.connect(self.onItemClicked)

        self.loadFeed()
        self.feedJSON = None
        self.kurwaParent = kurwaParent # This is a workaround to access the parent QStackedWidget from the plugin system

    def loadFeed(self, append=False):
        if not append:
            self.feedList.clear()
            self.page = 1
            self.feedJSON = []
        try:
            response = requests.get(getFeedURL(page=self.page))
            response.raise_for_status()  # Raise an error for bad responses
            data = response.json()
            for post in data.get('posts', []):
                item = QListWidgetItem(post['title'])
                item.setData(Qt.UserRole, post)  # Store the full post data
                self.feedList.addItem(item)
                self.feedJSON.append(post)
                if self.shouldArchivePosts:
                    # Save the post data to a JSON file
                    with open(f"feedViewerArchive/post_{post['external_id']}.json", 'w', encoding='utf-8') as f:
                        json.dump(post, f, ensure_ascii=False, indent=4)
                        print(f"Dumped post data to feedViewerArchive/post_{post['external_id']}.json")
            print("Feed data pulled! Archiving is extremely recommended, since this feature might stop working at any time as it is from a removed part of Character AI.")
        except requests.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to load feed: {e}")

    def checkScroll(self, value):
        # If we've reached the bottom, load the next page
        if value == self.feedList.verticalScrollBar().maximum():
            self.page += 1
            self.loadFeed(append=True)

    def onItemClicked(self, item):
        post_data = item.data(Qt.UserRole)
        post_id = post_data.get("external_id")
        if not post_id:
            return
        self.viewPostDetails(post_id)
    def viewPostDetails(self, post_id):
        menu = QMenu(self)
        viewDetailsAction = menu.addAction("View Post Details")
        #openBrowserAction = menu.addAction("Open in Browser") # This doesnt work since it opens the API URL, not the post URL.
        # (the original frontend was shut down, so the post URL is not available anymore. this is a replacement frontend that uses the API to get the post details)
        action = menu.exec_(QCursor.pos())

        if action == viewDetailsAction:
            try:
                url = f"https://plus.character.ai/chat/post/?post={post_id}"
                response = requests.get(url)
                response.raise_for_status()
                print(f"Loaded post details from {url}")
            except requests.RequestException as e:
                QMessageBox.critical(self, "Error", f"Failed to load post details: {e}")
                return

            data = response.json()
            if self.shouldArchivePosts:
                # Save full post data to a JSON file
                with open(f"feedViewerArchive/post_{post_id}_full.json", 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    print(f"Dumped full post data to feedViewerArchive/post_{post_id}_full.json")
            post_details = data.get("post")
            if not post_details:
                QMessageBox.critical(self, "Error", "Post details not found in the response.")
                return

            # Create a new widget to show post details in the main window
            detailsWidget = QWidget(self)
            detailsLayout = QVBoxLayout(detailsWidget)

            # Back button to return to the feed list
            backButton = QPushButton("Back")
            detailsLayout.addWidget(backButton)
            backButton.clicked.connect(lambda: self.kurwaParent.setCurrentWidget(self))
            
            # Add a scroll area for the content
            scrollArea = QScrollArea()
            scrollArea.setWidgetResizable(True)
            detailsLayout.addWidget(scrollArea)
            contentWidget = QWidget()
            scrollArea.setWidget(contentWidget)
            contentLayout = QVBoxLayout(contentWidget)

            # Display post details (except comments)
            for key, value in post_details.items():
                if key == "comments":
                    continue
                label = QLabel(f"<b>{key}:</b> {value}")
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                contentLayout.addWidget(label)

            # Create a section for comments
            commentsLabel = QLabel("<b>Comments: (these fully work unlike actual post data)</b>")
            contentLayout.addWidget(commentsLabel)
            commentList = QListWidget()
            contentLayout.addWidget(commentList)

            # Recursively add comments and their children
            def add_comment(comment, indent=0):
                # Create a container widget for the comment
                padding = indent  # Use the indent level for left padding
                commentWidget = QWidget()
                hLayout = QHBoxLayout(commentWidget)
                hLayout.setContentsMargins(padding, 5, 5, 5)  # Padding on the left only
                hLayout.setSpacing(10)

                # Load the avatar
                avatar_file = comment.get("src__user__account__avatar_file_name", "")
                avatar_url = "https://characterai.io/i/80/static/avatars/" + avatar_file
                avatarLabel = QLabel()
                try:
                    avatar_response = requests.get(avatar_url)
                    avatar_data = avatar_response.content
                    pixmap = QPixmap()
                    pixmap.loadFromData(avatar_data)

                    # Round the pixmap (make circular)
                    size = 40
                    pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    rounded = QPixmap(size, size)
                    rounded.fill(Qt.transparent)

                    painter = QPainter(rounded)
                    painter.setRenderHint(QPainter.Antialiasing)
                    path = QPainterPath()
                    path.addEllipse(0, 0, size, size)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()

                    avatarLabel.setPixmap(rounded)
                except Exception as e:
                    avatarLabel.setText("No Image")

                # Create container for text and copy button
                textContainer = QWidget()
                vLayout = QVBoxLayout(textContainer)
                vLayout.setContentsMargins(0, 0, 0, 0)
                vLayout.setSpacing(2)

                # Display the comment text just after the avatar
                username = comment.get('src__name', 'Unknown')
                text_content = comment.get('text', '')
                textLabel = QLabel(f"<b>{username}</b>: {text_content}")
                textLabel.setWordWrap(True)
                textLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
                vLayout.addWidget(textLabel)

                # Add a "copy comment" button
                copyButton = QPushButton("Copy comment")
                copyButton.setFixedSize(100, 20)
                copyButton.clicked.connect(lambda: QApplication.clipboard().setText(text_content))
                vLayout.addWidget(copyButton, alignment=Qt.AlignLeft)

                # Add avatar and text container to the layout
                hLayout.addWidget(avatarLabel)
                hLayout.addWidget(textContainer)

                # Insert the custom widget into the comment list
                listItem = QListWidgetItem()
                listItem.setSizeHint(commentWidget.sizeHint())  # Set the size hint for the item
                commentList.addItem(listItem)
                commentList.setItemWidget(listItem, commentWidget)

                # Recursively add child comments with increased left padding
                for child in comment.get("children", []):
                    add_comment(child, padding + 20)

            for comment in data.get("comments", []):
                add_comment(comment)
                print("Adding comment!")

            # Show the details widget in the main window by adding and switching it in the QStackedWidget
            self.kurwaParent.addWidget(detailsWidget)
            self.kurwaParent.setCurrentWidget(detailsWidget)

        #elif action == openBrowserAction:
        #    QDesktopServices.openUrl(QUrl(f"https://plus.character.ai/chat/post/?post={post_id}"))
        
    def createAPost(self):
        # Create a dialog to input post details
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Post")
        dialogLayout = QVBoxLayout(dialog)

        titleInput = QLineEdit(dialog)
        titleInput.setPlaceholderText("Post Title")
        dialogLayout.addWidget(titleInput)

        contentInput = QTextEdit(dialog)
        contentInput.setPlaceholderText("Post Content")
        dialogLayout.addWidget(contentInput)

        createButton = QPushButton("Create Post", dialog)
        createButton.clicked.connect(lambda: 
                                        self.viewPostDetails(
                                            createPost(title=titleInput.text(), content=contentInput.toPlainText(),topic="puUoF8HHLL8QrsaGaZQ-hXz-pmsSffRxtEDGUZz5iAE")
                                            )
                                    )
        dialogLayout.addWidget(createButton)

        dialog.exec()

layout = tab["layout"]
owner = QStackedWidget()
feedViewer = FeedViewer(kurwaParent=owner) # Do not use the parent argument, since it will make QT mistakenly place the widget in the wrong place.
owner.addWidget(feedViewer)
layout.addWidget(owner)