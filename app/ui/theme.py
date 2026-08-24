"""Central visual theme for the AURA desktop application."""

from __future__ import annotations

AURA_DARK_THEME = """
QMainWindow, QWidget#auraCentralWidget {
    background: #18212b;
    color: #e8eef5;
}
QLabel#auraTitle {
    color: #f2f6fa;
    font-size: 30px;
    font-weight: 600;
}
QLabel#auraSubtitle {
    color: #aebdcb;
    font-size: 15px;
}
QTextBrowser#conversationDisplay {
    background: #222e3a;
    border: 1px solid #3b4b5c;
    border-radius: 6px;
    color: #e8eef5;
    font-size: 14px;
    padding: 8px;
}
QWidget#confirmationPanel {
    background: #263b4e;
    border: 1px solid #4d7398;
    border-radius: 6px;
}
QLabel#confirmationLabel {
    color: #e8eef5;
    font-size: 13px;
}
QLineEdit#messageInput {
    background: #222e3a;
    border: 1px solid #4a5b6c;
    border-radius: 5px;
    color: #f2f6fa;
    padding: 9px;
}
QLineEdit#messageInput:disabled {
    background: #1d2731;
    color: #7f91a2;
}
QPushButton#sendButton, QPushButton#allowButton {
    background: #4f86b8;
    border: none;
    border-radius: 5px;
    color: #ffffff;
    font-weight: 600;
    padding: 9px 18px;
}
QPushButton#sendButton:hover, QPushButton#allowButton:hover {
    background: #679dcd;
}
QPushButton#sendButton:disabled, QPushButton#allowButton:disabled {
    background: #3b5267;
    color: #9aaaba;
}
QPushButton#cancelButton {
    background: #2d3a47;
    border: 1px solid #596b7d;
    border-radius: 5px;
    color: #e8eef5;
    padding: 8px 16px;
}
QPushButton#cancelButton:hover {
    background: #3a4c5d;
}
QStatusBar {
    background: #18212b;
    color: #aebdcb;
}
"""

__all__ = ["AURA_DARK_THEME"]
