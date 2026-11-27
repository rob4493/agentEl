export type IconName = 'document' | 'spark' | 'shield' | 'facts' | 'alert' | 'flask' | 'edit' | 'refresh' | 'close' | 'check' | 'copy' | 'chevron' | 'info';

const iconPaths: Record<IconName,string[]> = {
  document:['M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z','M14 3v6h6','M8 13h8M8 17h6'],
  spark:['m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z','M20 3v4M18 5h4'],
  shield:['m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z','m8 12 3 3 5-6'],
  facts:['M9 6h11M9 12h11M9 18h11','M4 6h.01M4 12h.01M4 18h.01'],
  alert:['m12 3 10 18H2Z','M12 9v5M12 17h.01'],
  flask:['M9 3h6M10 3v7l-6 9a1.3 1.3 0 0 0 1 2h14a1.3 1.3 0 0 0 1-2l-6-9V3','M8 15h8'],
  edit:['m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15Z'],
  refresh:['M20 7v5h-5M4 17v-5h5','M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1'],
  close:['m6 6 12 12M18 6 6 18'],
  check:['m5 12 4 4L19 6'],
  copy:['M9 9h11v12H9Z','M15 9V3H3v12h6'],
  chevron:['m8 10 4 4 4-4'],
  info:['M12 11v6M12 7h.01','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
};

export function WorkspaceIcon({name,className=''}:{name:IconName;className?:string}) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name].map((path,index)=><path d={path} key={index}/>)}</svg>;
}
