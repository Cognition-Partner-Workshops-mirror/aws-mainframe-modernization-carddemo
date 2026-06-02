import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridReadyEvent } from 'ag-grid-community';
import { BalanceService } from '../../services/balance.service';
import { KeyConfigurationService } from '../../services/key-configuration.service';

/**
 * AG Grid component displaying the DAILY_BALANCES data.
 * Supports filtering by address, year, and month with dynamic column headers
 * derived from KEY_CONFIGURATION table.
 */
@Component({
  selector: 'app-balance-grid',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridModule],
  template: `
    <div class="card">
      <h2>Daily Balance Grid</h2>
      <div class="filters">
        <select [(ngModel)]="selectedAddress" (change)="applyFilter()">
          <option value="">All Addresses</option>
          <option *ngFor="let addr of addresses" [value]="addr">{{ addr }}</option>
        </select>
        <select [(ngModel)]="selectedYear" (change)="applyFilter()">
          <option [ngValue]="null">All Years</option>
          <option *ngFor="let year of years" [ngValue]="year">{{ year }}</option>
        </select>
        <select [(ngModel)]="selectedMonth" (change)="applyFilter()">
          <option [ngValue]="null">All Months</option>
          <option *ngFor="let m of months" [ngValue]="m.value">{{ m.label }}</option>
        </select>
        <button class="btn btn-primary" (click)="applyFilter()">Apply</button>
        <button class="btn btn-secondary" (click)="resetFilters()">Reset</button>
      </div>
    </div>
    <div class="card grid-container">
      <ag-grid-angular
        class="ag-theme-alpine"
        [rowData]="rowData"
        [columnDefs]="columnDefs"
        [defaultColDef]="defaultColDef"
        [pagination]="true"
        [paginationPageSize]="25"
        (gridReady)="onGridReady($event)">
      </ag-grid-angular>
    </div>
  `,
  styles: [`
    .filters {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
      align-items: center;
    }
    .filters select {
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }
    .grid-container {
      height: 600px;
    }
    ag-grid-angular {
      width: 100%;
      height: 100%;
    }
  `]
})
export class BalanceGridComponent implements OnInit {
  rowData: any[] = [];
  columnDefs: ColDef[] = [];
  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
    minWidth: 100
  };

  addresses: string[] = [];
  years: number[] = [];
  months = [
    { value: 1, label: 'January' }, { value: 2, label: 'February' },
    { value: 3, label: 'March' }, { value: 4, label: 'April' },
    { value: 5, label: 'May' }, { value: 6, label: 'June' },
    { value: 7, label: 'July' }, { value: 8, label: 'August' },
    { value: 9, label: 'September' }, { value: 10, label: 'October' },
    { value: 11, label: 'November' }, { value: 12, label: 'December' }
  ];

  selectedAddress = '';
  selectedYear: number | null = null;
  selectedMonth: number | null = null;

  private keyNames: Map<number, string> = new Map();

  constructor(
    private balanceService: BalanceService,
    private keyConfigService: KeyConfigurationService
  ) {}

  ngOnInit(): void {
    this.loadKeyConfiguration();
    this.loadFilterOptions();
    this.loadData();
  }

  onGridReady(params: GridReadyEvent): void {
    params.api.sizeColumnsToFit();
  }

  applyFilter(): void {
    const filters: { [key: string]: string | number | null } = {
      key1: this.selectedAddress || null,
      year: this.selectedYear,
      month: this.selectedMonth
    };
    this.balanceService.getByFilters(filters).subscribe(data => {
      this.rowData = data;
    });
  }

  resetFilters(): void {
    this.selectedAddress = '';
    this.selectedYear = null;
    this.selectedMonth = null;
    this.loadData();
  }

  private loadKeyConfiguration(): void {
    this.keyConfigService.getActive().subscribe(keys => {
      keys.forEach((k: any) => this.keyNames.set(k.keyId, k.keyName));
      this.buildColumnDefs();
    });
  }

  private loadFilterOptions(): void {
    this.balanceService.getAddresses().subscribe(addrs => this.addresses = addrs);
    this.balanceService.getYears().subscribe(yrs => this.years = yrs);
  }

  private loadData(): void {
    this.balanceService.getAll().subscribe(data => this.rowData = data);
  }

  /** Build AG Grid column definitions using KEY_CONFIGURATION names. */
  private buildColumnDefs(): void {
    const keyCols: ColDef[] = [];
    for (let i = 1; i <= 16; i++) {
      const name = this.keyNames.get(i) || `Key ${i}`;
      keyCols.push({
        headerName: name,
        field: `key${i}`,
        hide: i > 6
      });
    }

    const dayCols: ColDef[] = [];
    dayCols.push({ headerName: 'Prev Month End', field: 'day0Balance', type: 'numericColumn' });
    for (let d = 1; d <= 31; d++) {
      dayCols.push({
        headerName: `Day ${d}`,
        field: `day${d}Balance`,
        type: 'numericColumn'
      });
    }

    this.columnDefs = [
      ...keyCols,
      { headerName: 'Year', field: 'balanceYear' },
      { headerName: 'Month', field: 'balanceMonth' },
      ...dayCols
    ];
  }
}
