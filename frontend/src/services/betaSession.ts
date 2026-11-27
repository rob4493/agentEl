// Codes stay only in module memory: never localStorage, URLs or telemetry.
let accessCode='';
const listeners=new Set<()=>void>();
export function getAccessCode(){return accessCode;}
export function setAccessCode(value:string){accessCode=value;for(const listener of listeners)listener();}
export function onAccessChange(listener:()=>void){listeners.add(listener);return ()=>{listeners.delete(listener);};}
