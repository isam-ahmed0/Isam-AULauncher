"""News page widgets — Markdown rendering with remote image loading (PySide6)."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap, QTextDocument
from PySide6.QtWidgets import QTextBrowser

from config import REQUEST_TIMEOUT


class NewsBrowser(QTextBrowser):
    """Markdown viewer that fetches http(s) images referenced in the message.

    QTextDocument does not resolve remote resources on its own, so
    ``loadResource`` pulls image bytes through the shared NetworkManager
    session and caches the pixmaps for later renders.
    """

    _image_cache = {}

    def __init__(self, network=None, parent=None):
        super().__init__(parent)
        self._network = network
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setPlaceholderText("No news right now. Check back later.")

    def loadResource(self, itype, name):
        try:
            if (
                itype == QTextDocument.ResourceType.ImageResource
                and isinstance(name, QUrl)
                and name.scheme() in ("http", "https")
                and self._network is not None
            ):
                url = name.toString()
                pm = self._image_cache.get(url)
                if pm is None:
                    try:
                        r = self._network.session.get(url, timeout=REQUEST_TIMEOUT)
                        if r.ok:
                            candidate = QPixmap()
                            if candidate.loadFromData(r.content) and not candidate.isNull():
                                pm = candidate
                                self._image_cache[url] = pm
                    except Exception:
                        pass
                if pm is not None:
                    return pm
        except Exception:
            pass
        return super().loadResource(itype, name)
