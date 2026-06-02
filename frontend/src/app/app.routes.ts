import { Routes } from '@angular/router';
import { BalanceGridComponent } from './components/balance-grid/balance-grid.component';
import { ReportsComponent } from './components/reports/reports.component';

/**
 * Application routes:
 * - /balances (default): AG Grid view of daily balances
 * - /reports: Embedded Superset dashboard or link to Superset UI
 */
export const routes: Routes = [
  { path: '', redirectTo: 'balances', pathMatch: 'full' },
  { path: 'balances', component: BalanceGridComponent },
  { path: 'reports', component: ReportsComponent }
];
