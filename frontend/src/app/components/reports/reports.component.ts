import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

/**
 * Reports component that embeds or links to the Apache Superset dashboard.
 * Provides both an iframe embed option and a direct link to open Superset.
 */
@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="card">
      <div class="reports-header">
        <h2>Balance Rollup &amp; Transfer Reporting</h2>
        <p class="description">
          Interactive dashboards powered by Apache Superset. View balance rollups,
          monthly trends, and detailed breakdowns with cross-filtering support.
        </p>
        <div class="actions">
          <button class="btn btn-primary" (click)="openSuperset()">
            Open Superset Dashboard
          </button>
          <button class="btn btn-secondary" (click)="toggleEmbed()">
            {{ showEmbed ? 'Hide' : 'Show' }} Embedded View
          </button>
        </div>
      </div>
    </div>
    <div class="card embed-container" *ngIf="showEmbed">
      <iframe
        [src]="supersetUrl"
        width="100%"
        height="800"
        frameborder="0"
        title="Superset Dashboard">
      </iframe>
    </div>
    <div class="card info-panel" *ngIf="!showEmbed">
      <h3>Available Dashboards</h3>
      <ul class="dashboard-list">
        <li>
          <strong>Balance Grid by Address &amp; Month</strong>
          <p>Pivot table with rows by Address, columns Day0-Day31, filterable by month/year</p>
        </li>
        <li>
          <strong>Monthly Total Balances by Address</strong>
          <p>Bar chart showing monthly totals grouped by address</p>
        </li>
        <li>
          <strong>Balance Trend Over 12 Months</strong>
          <p>Line chart with per-address monthly totals across the year</p>
        </li>
        <li>
          <strong>Detailed Balance View</strong>
          <p>Full table with all 16 keys and day columns with pagination</p>
        </li>
      </ul>
      <div class="credentials">
        <h4>Access Credentials</h4>
        <p>Username: <code>admin</code> | Password: <code>admin</code></p>
        <p>URL: <a href="http://localhost:8088" target="_blank">http://localhost:8088</a></p>
      </div>
    </div>
  `,
  styles: [`
    .reports-header {
      margin-bottom: 16px;
    }
    .description {
      color: #666;
      margin: 8px 0 16px;
    }
    .actions {
      display: flex;
      gap: 12px;
    }
    .embed-container {
      padding: 0;
      overflow: hidden;
    }
    .embed-container iframe {
      display: block;
    }
    .info-panel h3 {
      margin-bottom: 12px;
      color: #1976d2;
    }
    .dashboard-list {
      list-style: none;
      padding: 0;
    }
    .dashboard-list li {
      padding: 12px 0;
      border-bottom: 1px solid #eee;
    }
    .dashboard-list li:last-child {
      border-bottom: none;
    }
    .dashboard-list p {
      color: #666;
      margin-top: 4px;
      font-size: 14px;
    }
    .credentials {
      margin-top: 20px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 4px;
    }
    .credentials code {
      background: #e0e0e0;
      padding: 2px 6px;
      border-radius: 3px;
    }
  `]
})
export class ReportsComponent {
  showEmbed = false;
  supersetUrl: SafeResourceUrl;

  constructor(private sanitizer: DomSanitizer) {
    // Superset dashboard URL - adjust dashboard ID as needed after initial setup
    this.supersetUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
      'http://localhost:8088/superset/dashboard/1/'
    );
  }

  /** Open Superset in a new browser tab. */
  openSuperset(): void {
    window.open('http://localhost:8088', '_blank');
  }

  /** Toggle the embedded iframe view. */
  toggleEmbed(): void {
    this.showEmbed = !this.showEmbed;
  }
}
