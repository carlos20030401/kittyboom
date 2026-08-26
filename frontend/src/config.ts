const developmentApi='http://localhost:8000/api/v1';
export const API_URL=(import.meta.env.VITE_API_URL||developmentApi).replace(/\/$/,'');
export const API_ORIGIN=API_URL.replace(/\/api\/v1$/,'');
export const assetUrl=(value?:string|null)=>!value?null:/^https?:\/\//i.test(value)?value:`${API_ORIGIN}${value}`;
