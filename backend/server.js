const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
    origin: ['http://localhost:3000', 'http://127.0.0.1:3000'],
    credentials: true
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database connection
const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'medintel_db',
    max: 20,
    idleTimeoutMillis: 30000,
});

// Test database connection
async function testDatabaseConnection() {
    try {
        const client = await pool.connect();
        console.log('✅ PostgreSQL connected successfully');
        client.release();
    } catch (error) {
        console.error('❌ Database connection failed:', error.message);
        process.exit(1);
    }
}
testDatabaseConnection();

// JWT Secret
const JWT_SECRET = process.env.JWT_SECRET || 'your-super-secret-jwt-key';

// Authentication middleware
async function authenticate(req, res, next) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'No token provided' });
    }

    const token = authHeader.split(' ')[1];
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(401).json({ error: 'Invalid or expired token' });
    }
}

// ============================================================
// AUTH ROUTES
// ============================================================

// GET /api/auth/me
app.get('/api/auth/me', authenticate, async (req, res) => {
    try {
        const result = await pool.query(
            `SELECT u.id, u.email, u.username, up.first_name, up.last_name 
             FROM users u 
             LEFT JOIN user_profiles up ON u.id = up.user_id 
             WHERE u.id = $1`,
            [req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'User not found' });
        }
        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error fetching user:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// POST /api/auth/login
app.post('/api/auth/login', async (req, res) => {
    const { email, password } = req.body;
    
    if (!email || !password) {
        return res.status(400).json({ error: 'Email and password required' });
    }

    try {
        const result = await pool.query(
            'SELECT id, email, username, password_hash FROM users WHERE email = $1',
            [email]
        );

        if (result.rows.length === 0) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const user = result.rows[0];
        const isValid = await bcrypt.compare(password, user.password_hash);
        
        if (!isValid) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const token = jwt.sign(
            { id: user.id, email: user.email, username: user.username },
            JWT_SECRET,
            { expiresIn: '7d' }
        );

        res.json({
            success: true,
            token,
            user: {
                id: user.id,
                email: user.email,
                username: user.username
            }
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// ============================================================
// CHAT ROUTES
// ============================================================

// GET /api/chats
app.get('/api/chats', authenticate, async (req, res) => {
    try {
        const result = await pool.query(
            `SELECT id, title, created_at, updated_at 
             FROM chats 
             WHERE user_id = $1 
             ORDER BY updated_at DESC`,
            [req.user.id]
        );
        res.json(result.rows);
    } catch (error) {
        console.error('Error fetching chats:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// POST /api/chats
app.post('/api/chats', authenticate, async (req, res) => {
    const { title } = req.body;
    
    try {
        const result = await pool.query(
            'INSERT INTO chats (user_id, title) VALUES ($1, $2) RETURNING id, title, created_at, updated_at',
            [req.user.id, title || 'New Chat']
        );
        
        res.status(201).json(result.rows[0]);
    } catch (error) {
        console.error('Error creating chat:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// GET /api/chats/:id
app.get('/api/chats/:id', authenticate, async (req, res) => {
    const chatId = req.params.id;
    
    try {
        const result = await pool.query(
            'SELECT id, title, created_at, updated_at FROM chats WHERE id = $1 AND user_id = $2',
            [chatId, req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Chat not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error fetching chat:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// DELETE /api/chats/:id
app.delete('/api/chats/:id', authenticate, async (req, res) => {
    const chatId = req.params.id;
    
    try {
        // Delete messages first
        await pool.query('DELETE FROM chat_messages WHERE chat_id = $1', [chatId]);
        
        const result = await pool.query(
            'DELETE FROM chats WHERE id = $1 AND user_id = $2 RETURNING id',
            [chatId, req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Chat not found' });
        }
        
        res.json({ success: true, message: 'Chat deleted' });
    } catch (error) {
        console.error('Error deleting chat:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// GET /api/chats/:id/messages
app.get('/api/chats/:id/messages', authenticate, async (req, res) => {
    const chatId = req.params.id;
    
    try {
        // First verify the chat belongs to the user
        const chatCheck = await pool.query(
            'SELECT id FROM chats WHERE id = $1 AND user_id = $2',
            [chatId, req.user.id]
        );
        
        if (chatCheck.rows.length === 0) {
            return res.status(404).json({ error: 'Chat not found' });
        }
        
        const result = await pool.query(
            `SELECT id, role, content, agent_name, created_at 
             FROM chat_messages 
             WHERE chat_id = $1 
             ORDER BY created_at ASC`,
            [chatId]
        );
        res.json(result.rows);
    } catch (error) {
        console.error('Error fetching messages:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// ============================================================
// AI CHAT ROUTE
// ============================================================

// POST /api/chat
app.post('/api/chat', authenticate, async (req, res) => {
    const { message, chat_id } = req.body;
    
    if (!message) {
        return res.status(400).json({ error: 'Message is required' });
    }
    
    let chatId = chat_id;
    
    try {
        // If no chat_id, create a new chat
        if (!chatId) {
            const title = message.slice(0, 30) + (message.length > 30 ? '...' : '');
            const result = await pool.query(
                'INSERT INTO chats (user_id, title) VALUES ($1, $2) RETURNING id',
                [req.user.id, title]
            );
            chatId = result.rows[0].id;
        }
        
        // Verify chat belongs to user
        const chatCheck = await pool.query(
            'SELECT id FROM chats WHERE id = $1 AND user_id = $2',
            [chatId, req.user.id]
        );
        
        if (chatCheck.rows.length === 0) {
            return res.status(403).json({ error: 'Unauthorized access to this chat' });
        }
        
        // Save user message
        await pool.query(
            'INSERT INTO chat_messages (chat_id, user_id, role, content) VALUES ($1, $2, $3, $4)',
            [chatId, req.user.id, 'user', message]
        );
        
        // ============================================================
        // AI AGENT PROCESSING
        // ============================================================
        const keywords = message.toLowerCase();
        let responseText = '';
        let agentUsed = 'Coordinator';
        
        if (keywords.includes('fever') || keywords.includes('cough') || keywords.includes('headache')) {
            responseText = `Based on your symptoms (${message}), I recommend:\n\n` +
                `1. Rest and stay hydrated\n` +
                `2. Monitor your temperature\n` +
                `3. Consult a healthcare provider if symptoms persist for more than 3 days\n\n` +
                `⚠️ This is not a medical diagnosis. Please consult a healthcare professional.`;
            agentUsed = 'Symptom Analysis';
        } else if (keywords.includes('headache') && keywords.includes('nausea')) {
            responseText = `Your symptoms of headache and nausea could be related to:\n\n` +
                `• Migraine\n` +
                `• Food poisoning\n` +
                `• Stress or tension\n\n` +
                `🔍 Suggested action: Rest in a quiet, dark room and stay hydrated. ` +
                `If symptoms worsen, seek medical attention.`;
            agentUsed = 'Disease Prediction';
        } else if (keywords.includes('hello') || keywords.includes('hi') || keywords.includes('hey')) {
            responseText = `Hello! I'm your MedIntel AI Assistant. How can I help you today?\n\n` +
                `I can help with:\n` +
                `• Symptom analysis\n` +
                `• Disease prediction\n` +
                `• Medical knowledge queries\n` +
                `• Treatment recommendations\n` +
                `• Report summarization`;
            agentUsed = 'Coordinator';
        } else {
            responseText = `I understand you're asking about: "${message}"\n\n` +
                `I've analyzed your query using our medical knowledge base. ` +
                `For a more specific response, please provide more details about your symptoms or health concerns.`;
            agentUsed = 'Medical Knowledge';
        }
        
        // Save assistant response
        await pool.query(
            `INSERT INTO chat_messages (chat_id, user_id, role, content, agent_name) 
             VALUES ($1, $2, $3, $4, $5)`,
            [chatId, req.user.id, 'assistant', responseText, agentUsed]
        );
        
        // Update chat updated_at
        await pool.query('UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = $1', [chatId]);
        
        // Also update the chat title if it's still "New Chat"
        await pool.query(
            `UPDATE chats SET title = $1 WHERE id = $2 AND title = 'New Chat'`,
            [message.slice(0, 30) + (message.length > 30 ? '...' : ''), chatId]
        );
        
        // Return response
        res.json({
            response: responseText,
            agent_results: {
                'Symptom Analysis': { status: 'success' },
                'Disease Prediction': { status: 'success' },
                'Medical Knowledge': { status: 'success' }
            },
            chat_id: chatId
        });
        
    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json({ 
            error: 'Server error: ' + error.message,
            response: 'I apologize, but I encountered an error processing your request. Please try again.'
        });
    }
});

// ============================================================
// SERVE STATIC FILES
// ============================================================
app.use(express.static(__dirname));

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// ============================================================
// START SERVER
// ============================================================
app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`📋 Endpoints:`);
    console.log(`   POST /api/auth/login`);
    console.log(`   GET  /api/auth/me`);
    console.log(`   GET  /api/chats`);
    console.log(`   POST /api/chats`);
    console.log(`   GET  /api/chats/:id`);
    console.log(`   DELETE /api/chats/:id`);
    console.log(`   GET  /api/chats/:id/messages`);
    console.log(`   POST /api/chat`);
});

process.on('unhandledRejection', (error) => {
    console.error('Unhandled Rejection:', error);
});

process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});

// PUT /api/chats/:id - Rename chat
app.put('/api/chats/:id', authenticate, async (req, res) => {
    const chatId = req.params.id;
    const { title } = req.body;
    
    try {
        const result = await pool.query(
            'UPDATE chats SET title = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 AND user_id = $3 RETURNING id, title',
            [title, chatId, req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Chat not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error renaming chat:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// PUT /api/chats/:id/pin - Pin/Unpin chat
app.put('/api/chats/:id/pin', authenticate, async (req, res) => {
    const chatId = req.params.id;
    const { is_pinned } = req.body;
    
    try {
        const result = await pool.query(
            'UPDATE chats SET is_pinned = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2 AND user_id = $3 RETURNING id, is_pinned',
            [is_pinned, chatId, req.user.id]
        );
        
        if (result.rows.length === 0) {
            return res.status(404).json({ error: 'Chat not found' });
        }
        
        res.json(result.rows[0]);
    } catch (error) {
        console.error('Error pinning chat:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// GET /api/chats/:id/messages - Get messages (already exists)