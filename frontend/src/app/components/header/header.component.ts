import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

/**
 * Navigation header component with links to Balance Grid and Reports (Superset).
 */
@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="app-header">
      <div class="header-content">
        <h1 class="app-title">Balance Transfer</h1>
        <nav class="nav-links">
          <a routerLink="/balances" routerLinkActive="active" class="nav-link">
            Balances
          </a>
          <a routerLink="/reports" routerLinkActive="active" class="nav-link">
            Reports
          </a>
        </nav>
      </div>
    </header>
  `,
  styles: [`
    .app-header {
      background-color: #1976d2;
      color: white;
      padding: 0 20px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .header-content {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
    }
    .app-title {
      font-size: 20px;
      font-weight: 500;
    }
    .nav-links {
      display: flex;
      gap: 16px;
    }
    .nav-link {
      color: rgba(255,255,255,0.8);
      text-decoration: none;
      padding: 8px 16px;
      border-radius: 4px;
      transition: background-color 0.2s;
    }
    .nav-link:hover {
      background-color: rgba(255,255,255,0.1);
      color: white;
    }
    .nav-link.active {
      background-color: rgba(255,255,255,0.2);
      color: white;
    }
  `]
})
export class HeaderComponent {}
