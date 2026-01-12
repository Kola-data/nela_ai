import React from 'react';
import './Navbar.css';

function Navbar({ user, onLogout }) {
  return (
    <nav className="navbar">
      <div className="navbar-content">
        <a href="/dashboard" className="navbar-brand">
          ✨ Nela AI
        </a>
        <div className="navbar-menu">
          {user && (
            <div className="user-info">
              <span className="user-name">{user.full_name || user.username}</span>
              <span className="user-email">{user.email}</span>
            </div>
          )}
          <button onClick={onLogout} className="btn btn-secondary">
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
