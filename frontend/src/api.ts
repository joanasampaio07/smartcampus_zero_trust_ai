const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
export function token(){return sessionStorage.getItem("access_token");}
export async function api(path:string, options:RequestInit={}){
 const headers=new Headers(options.headers); headers.set("Content-Type","application/json");
 if(token()) headers.set("Authorization",`Bearer ${token()}`);
 const r=await fetch(`${BASE}${path}`,{...options,headers});
 if(!r.ok){const body=await r.json().catch(()=>({}));throw new Error(body.detail||`HTTP ${r.status}`);}
 return r.status===204?null:r.json();
}
export {BASE};
