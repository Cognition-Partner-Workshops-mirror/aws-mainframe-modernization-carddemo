import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

/**
 * Service for key configuration API.
 * Fetches dynamic column header names for the balance grid.
 */
@Injectable({
  providedIn: 'root'
})
export class KeyConfigurationService {
  private apiUrl = `${environment.apiUrl}/api/keys`;

  constructor(private http: HttpClient) {}

  /** Get all key configurations. */
  getAll(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  /** Get active key configurations only. */
  getActive(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/active`);
  }
}
