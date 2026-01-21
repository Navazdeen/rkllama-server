"""
Chat History Database Management

Handles persisting chat sessions and messages to SQLite database.
Features:
- Auto-generate chat titles from first user message
- Save/load chat history
- Search chats by title or model
- Clean up old chats
"""

import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional

# Get the directory where this file is located (rkllm_server folder)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "chat_history.db")
DB_DIR = os.path.dirname(DB_PATH)

# Ensure database directory exists
os.makedirs(DB_DIR, exist_ok=True)
print(f"[ChatDB] Database path: {DB_PATH}")

# Thread-safe database operations
db_lock = threading.Lock()


class ChatDatabase:
    """SQLite database for chat history management."""
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize database connection."""
        self.db_path = db_path
        self.initDatabase()
    
    def getConnection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def initDatabase(self):
        """Create database schema if not exists."""
        with db_lock:
            conn = self.getConnection()
            cursor = conn.cursor()
            
            # Create chats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model TEXT NOT NULL,
                    platform TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            conn.close()
    
    def createChat(self, chat_id: str, model: str, platform: str = "rk3588") -> bool:
        """Create new chat session in database."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                # Generate initial title from model name
                title = self._generateTitleFromModel(model)
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO chats (id, title, model, platform, created_at, updated_at, message_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (chat_id, title, model, platform, now, now, 0))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Error creating chat: {str(e)}")
                return False
    
    def addMessage(self, chat_id: str, role: str, content: str) -> bool:
        """Add message to chat."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO messages (chat_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (chat_id, role, content, now))
                
                # Update chat's updated_at and message_count
                cursor.execute('''
                    UPDATE chats 
                    SET updated_at = ?, message_count = message_count + 1
                    WHERE id = ?
                ''', (now, chat_id))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Error adding message: {str(e)}")
                return False
    
    def updateChatTitle(self, chat_id: str, new_title: str) -> bool:
        """Update chat title (called when first user message arrives)."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                cursor.execute('''
                    UPDATE chats 
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                ''', (new_title, now, chat_id))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Error updating title: {str(e)}")
                return False
    
    def getChat(self, chat_id: str) -> Optional[Dict]:
        """Get chat info by ID."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM chats WHERE id = ?', (chat_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return dict(row)
                return None
            except Exception as e:
                print(f"❌ Error getting chat: {str(e)}")
                return None
    
    def getChatMessages(self, chat_id: str) -> List[Dict]:
        """Get all messages for a chat."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT role, content FROM messages 
                    WHERE chat_id = ? 
                    ORDER BY timestamp ASC
                ''', (chat_id,))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [dict(row) for row in rows]
            except Exception as e:
                print(f"❌ Error getting messages: {str(e)}")
                return []
    
    def getAllChats(self) -> List[Dict]:
        """Get all chats, ordered by updated_at descending."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM chats 
                    ORDER BY updated_at DESC
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                return [dict(row) for row in rows]
            except Exception as e:
                print(f"❌ Error getting all chats: {str(e)}")
                return []
    
    def searchChats(self, query: str) -> List[Dict]:
        """Search chats by title or model."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                search_term = f"%{query}%"
                cursor.execute('''
                    SELECT * FROM chats 
                    WHERE title LIKE ? OR model LIKE ?
                    ORDER BY updated_at DESC
                ''', (search_term, search_term))
                
                rows = cursor.fetchall()
                conn.close()
                
                return [dict(row) for row in rows]
            except Exception as e:
                print(f"❌ Error searching chats: {str(e)}")
                return []
    
    def deleteChat(self, chat_id: str) -> bool:
        """Delete chat and all its messages."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                # Messages will be deleted due to CASCADE
                cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Error deleting chat: {str(e)}")
                return False
    
    def deleteAllChats(self) -> bool:
        """Delete all chats."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM messages')
                cursor.execute('DELETE FROM chats')
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"❌ Error deleting all chats: {str(e)}")
                return False
    
    def chatExists(self, chat_id: str) -> bool:
        """Check if chat exists."""
        with db_lock:
            try:
                conn = self.getConnection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT 1 FROM chats WHERE id = ?', (chat_id,))
                exists = cursor.fetchone() is not None
                
                conn.close()
                return exists
            except Exception as e:
                print(f"❌ Error checking chat: {str(e)}")
                return False
    
    @staticmethod
    def _generateTitleFromModel(model: str) -> str:
        """Generate chat title from model name."""
        # Remove file extensions and platform info
        title = model.split('.')[0]  # Remove .rkllm
        title = title.split('_rk')[0]  # Remove _rk3588 etc
        title = title.replace('-', ' ').replace('_', ' ')
        return f"Chat with {title.strip()}"
    
    @staticmethod
    def generateTitleFromMessage(message: str, model: str) -> str:
        """Generate appropriate title from first user message (simple extraction)."""
        try:
            # Take first 50 chars of message
            title = message.strip()[:50]
            
            # Remove special characters
            title = ''.join(c for c in title if c.isalnum() or c in ' -.,')
            
            # Capitalize
            title = title.strip()
            if len(title) > 1:
                title = title[0].upper() + title[1:]
            
            if title:
                return f"{title}"
            else:
                return ChatDatabase._generateTitleFromModel(model)
        except Exception:
            return ChatDatabase._generateTitleFromModel(model)
    
    @staticmethod
    def extractSummaryFromModelResponse(response: str, max_length: int = 60) -> str:
        """Extract and clean a model-generated summary for use as title."""
        try:
            if not response:
                return ""
            
            # Take first sentence or first max_length chars
            sentences = response.split('.')
            summary = sentences[0].strip() if sentences else response.strip()
            
            # Clean up
            summary = summary.replace('\n', ' ').strip()
            summary = ' '.join(summary.split())  # Normalize whitespace
            
            # Trim to max length
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + '...'
            
            # Capitalize first letter
            if summary and len(summary) > 0:
                summary = summary[0].upper() + summary[1:]
            
            return summary
        except Exception:
            return ""


# Global database instance
chatDb: Optional[ChatDatabase] = None


def initChatDatabase() -> ChatDatabase:
    """Initialize and return global database instance."""
    global chatDb
    if chatDb is None:
        chatDb = ChatDatabase()
    return chatDb


def getChatDatabase() -> ChatDatabase:
    """Get global database instance."""
    global chatDb
    if chatDb is None:
        chatDb = ChatDatabase()
    return chatDb
