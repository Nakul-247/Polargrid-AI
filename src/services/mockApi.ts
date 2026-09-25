/** API service. It uses FastAPI when reachable and preserves the offline demo fallback. */
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
async function request<T>(path:string, init?:RequestInit):Promise<T>{
 const response=await fetch(`${baseUrl}${path}`,{headers:{'Content-Type':'application/json',...(init?.headers ?? {})},...init});
 if(!response.ok) throw new Error(`API ${response.status}: ${await response.text()}`);
 return response.json() as Promise<T>;
}
export const api={
 health:()=>request<{status:string}>('/api/health'),
 scenarios:()=>request<Array<{id:string;name:string}>>('/api/scenarios'),
 scenario:(id:string)=>request(`/api/scenarios/${id}`),
 assumptions:()=>request('/api/assumptions'),
 simulate:(body:{scenario_id:string;reserve_floor_pct?:number;wind_cutout_ms?:number})=>request('/api/simulate',{method:'POST',body:JSON.stringify(body)}),
 compare:(body:{scenario_id:string})=>request('/api/compare',{method:'POST',body:JSON.stringify(body)})
};
