# SKELETON BLUEPRINT: UI Layout Implementation for CrewLauncher Home View
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QPushButton, QLabel, QFrame
)

class HomeViewSkeleton(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CrewLauncher - Home")
        self.resize(1000, 650)

        # Central Root Widget (Master Horizontal Split)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.root_layout = QHBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Sidebar Component (Left Column)
        self.setup_sidebar()

        # 2. Main Content Container (Right Column)
        self.setup_main_content()

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(80)  # Icon-only slim width as sketched

        layout = QVBoxLayout(self.sidebar)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(16)

        # 6 Sidebar Icon/Nav Buttons matching your sketch
        nav_icons = ["🏠", "📦", "🔧", "👤", "⚙️", "ℹ️"]
        for icon in nav_icons:
            btn = QPushButton(icon)
            btn.setFixedSize(50, 50)
            btn.setProperty("class", "NavIconBtn")
            layout.addWidget(btn)

        self.root_layout.addWidget(self.sidebar)

    def setup_main_content(self):
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        # --- TOP HEADER BAR ---
        header_layout = QHBoxLayout()

        brand_label = QLabel("CREW LAUNCHER")
        brand_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        user_info_label = QLabel("itchname - user code")
        version_label = QPushButton("Lau. ver.")
        version_label.setFixedWidth(80)

        header_layout.addWidget(brand_label)
        header_layout.addStretch()
        header_layout.addWidget(user_info_label)
        header_layout.addWidget(version_label)

        content_layout.addLayout(header_layout)

        # --- 2x2 GRID CONTENT AREA ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)

        # 1. Top-Left: Game Info & Launch Card
        game_card = QFrame()
        game_card.setProperty("class", "Card")
        game_layout = QVBoxLayout(game_card)

        game_title = QLabel("Among Us")
        game_title.setStyleSheet("font-size: 22px; font-weight: bold;")
        version_info = QLabel("Version: game version")
        size_info = QLabel("Size: game size")

        self.launch_btn = QPushButton("LAUNCH")
        self.launch_btn.setProperty("class", "PrimaryBtn")
        self.launch_btn.setFixedHeight(45)

        game_layout.addWidget(game_title)
        game_layout.addWidget(version_info)
        game_layout.addWidget(size_info)
        game_layout.addStretch()
        game_layout.addWidget(self.launch_btn)

        # 2. Top-Right: Custom Image / Note Card
        custom_card = QFrame()
        custom_card.setProperty("class", "Card")
        custom_layout = QVBoxLayout(custom_card)

        custom_placeholder = QLabel("User can add an custom image or note")
        custom_placeholder.setAlignment(Qt.AlignCenter)
        custom_placeholder.setStyleSheet("color: #888888;")
        custom_layout.addWidget(custom_placeholder)

        # 3. Bottom-Left: Mods Card
        mods_card = QFrame()
        mods_card.setProperty("class", "Card")
        mods_layout = QVBoxLayout(mods_card)

        mods_title = QLabel("Mods")
        mods_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        profile_label = QLabel("Profile: name")
        mods_count_label = QLabel("Mods: mods number")

        mods_layout.addWidget(mods_title)
        mods_layout.addWidget(profile_label)
        mods_layout.addWidget(mods_count_label)
        mods_layout.addStretch()

        # 4. Bottom-Right: Tools Card
        tools_card = QFrame()
        tools_card.setProperty("class", "Card")
        tools_layout = QVBoxLayout(tools_card)

        tools_title = QLabel("Tools")
        tools_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        quick_tools_label = QLabel("Quick Tools")
        quick_tools_label.setStyleSheet("font-size: 12px; color: #aaaaaa;")

        # 2x2 Grid inside the Tools card for buttons
        tools_btn_grid = QGridLayout()
        btn_loc = QPushButton("Change Location")
        btn_shortcut = QPushButton("Create Shortcut")
        btn_folder = QPushButton("Open Folder")
        btn_uninstall = QPushButton("Uninstall")
        btn_uninstall.setProperty("class", "DangerBtn")

        tools_btn_grid.addWidget(btn_loc, 0, 0)
        tools_btn_grid.addWidget(btn_shortcut, 0, 1)
        tools_btn_grid.addWidget(btn_folder, 1, 0)
        tools_btn_grid.addWidget(btn_uninstall, 1, 1)

        tools_layout.addWidget(tools_title)
        tools_layout.addWidget(quick_tools_label)
        tools_layout.addLayout(tools_btn_grid)
        tools_layout.addStretch()

        # Attach all 4 cards to the main grid layout
        grid_layout.addWidget(game_card, 0, 0)
        grid_layout.addWidget(custom_card, 0, 1)
        grid_layout.addWidget(mods_card, 1, 0)
        grid_layout.addWidget(tools_card, 1, 1)

        content_layout.addLayout(grid_layout)
        self.root_layout.addWidget(self.content_container)

if __name__ == "__main__":
    app = QApplication([])
    window = HomeViewSkeleton()
    window.show()
    app.exec()
