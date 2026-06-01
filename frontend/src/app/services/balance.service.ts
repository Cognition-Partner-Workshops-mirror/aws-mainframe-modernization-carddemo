import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

/**
 * Service to interact with the Balance Transfer backend API.
 * Used by AG Grid component to fetch and filter balance data.
 */
@Injectable({
  providedIn: 'root'
})
export class BalanceService {
  private apiUrl = `${environment.apiUrl}/api/balances`;

  constructor(private http: HttpClient) {}

  /** Fetch all balance records for AG Grid display. */
  getAll(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  /** Fetch balances filtered by address (KEY_1). */
  getByAddress(address: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/by-address/${encodeURIComponent(address)}`);
  }

  /** Fetch balances for a specific year and month. */
  getByPeriod(year: number, month: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/by-period/${year}/${month}`);
  }

  /** Fetch balances with multiple filter criteria. */
  getByFilters(filters: { [key: string]: string | number | null }): Observable<any[]> {
    let params = new HttpParams();
    Object.keys(filters).forEach(key => {
      const val = filters[key];
      if (val !== null && val !== undefined && val !== '') {
        params = params.set(key, val.toString());
      }
    });
    return this.http.get<any[]>(`${this.apiUrl}/filter`, { params });
  }

  /** Get distinct addresses for filter dropdown. */
  getAddresses(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/addresses`);
  }

  /** Get distinct years for filter dropdown. */
  getYears(): Observable<number[]> {
    return this.http.get<number[]>(`${this.apiUrl}/years`);
  }
}
