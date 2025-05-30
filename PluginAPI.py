import os
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QLineEdit, QPushButton, QMessageBox, QTextEdit, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QStackedWidget, QMenu, QScrollArea,
    QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIntValidator, QDoubleValidator
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextOption
import uuid
import json
from threading import Thread
import requests

class pluginAPI():
    def __init__(self, qmainwindowapplication,metdata):
        self.QMainWindow = qmainwindowapplication
        self.hasCreatedTab = False
        self.pluginMetadata = metdata
    
    def CreatePluginTab(self,tabName):
        if not self.hasCreatedTab:
            self.hasCreatedTab = True
            # Create a new tab in the main window
            widget = QWidget()
            layout = QVBoxLayout(widget)
            widget.setLayout(layout)
            widget.setObjectName("PluginTab_" + str(uuid.uuid4()))
            tab = self.QMainWindow.tabs.addTab(widget, tabName)
            return {
                "tabID": tab,
                "widget": widget,
                "layout": layout,
                "tabName": tabName,
            }
        else:
            raise Exception("A plugin tab has already been created. Only one plugin tab can be created per plugin.")
    
    def is_anonymous(self):
        return self.QMainWindow.guestMode
    
    def postWithAuthorization(self, url, data):
        if self.QMainWindow.authToken is None:
            raise Exception("Authorization token is not set. Please log in first.")
        headers = {            
            "Content-Type": "application/json",
            "Referer": "https://character.ai/",
            "User-Agent": "Mozilla/5.0 Characterinator/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Authorization": f"Token {self.QMainWindow.authToken}"  # Use the auth token from the main window
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to post data. Status code: {response.status_code}, Response: {response.text}")

class pluginmanager():
    def __init__(self,qmainwindowapplication):
        self.plugins = []
        self.QMainWindow = qmainwindowapplication
    
    def load_plugins(self):

        plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
        for filename in os.listdir(plugins_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_name = filename.split('.')[0]
                plugin_path = os.path.join(plugins_dir, filename)
                # Exec the plugin file in a new globals environment
                plugin_globals = {}
                with open(os.path.join(plugins_dir,f"{plugin_name}.json"), 'r') as plugin_json_file:
                    metadata = json.load(plugin_json_file)
                plugin_globals['pluginAPI'] = pluginAPI(self.QMainWindow,metadata)
                with open(plugin_path, 'r') as plugin_file:
                    if not metadata.get("doNotUseThread",False):
                        thread = Thread(target=exec, args=(plugin_file.read(), plugin_globals))
                        thread.start()
                    else:
                        exec(plugin_file.read(), plugin_globals)
                        thread = None
                    self.plugins.append({
                        'name': plugin_name,
                        'globals': plugin_globals,
                        'thread': thread
                    })
                    print(f"Loaded plugin: {plugin_name} in {'Main Thread' if metadata.get('doNotUseThread',False) else 'Dedicated Thread'}")  