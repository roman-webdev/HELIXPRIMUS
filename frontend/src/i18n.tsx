import {useEffect,useState} from 'react';
import {Globe,ChevronDown} from 'lucide-react';
import dictionaries from './translations.json';

export type Language='en'|'ru'|'uk';
export const LANGUAGE_KEY='helixprimus.language';
export const languages:Record<Language,string>={en:'English',ru:'Русский',uk:'Українська'};
const valid=(value:string|null):value is Language=>value!==null&&Object.hasOwn(languages,value);
const readLanguage=():Language=>{try{const value=localStorage.getItem(LANGUAGE_KEY);return valid(value)?value:'en';}catch{return 'en';}};
export type Translate=(text:string,error?:boolean)=>string;

export function translate(language:Language,text:string,error=false):string{
 if(language==='en')return text;
 const dictionary:Record<string,string>=dictionaries[language];
 if(Object.hasOwn(dictionary,text))return dictionary[text];
 // Localize explanation templates while preserving quoted customer evidence and technical policy keys.
 const phrases=['Matched customer phrases: ','Explicit customer references: ','Explicit order references: ','Exact policy key for the selected intent: '];
 for(const prefix of phrases){
  if(text.startsWith(prefix)){
   const ending='. Ordered rules select this intent.';
   return dictionary[prefix]+(text.endsWith(ending)?text.slice(prefix.length,-ending.length)+dictionary[ending]:text.slice(prefix.length));
  }
 }
 return error?dictionary['Request could not be completed']:text;
}

export function useLanguage(){
 const [language,setLanguage]=useState<Language>(readLanguage);
 useEffect(()=>{
  document.documentElement.lang=language;
  try{localStorage.setItem(LANGUAGE_KEY,language);}catch{/* Keep switching usable if browser storage is unavailable. */}
 },[language]);
 useEffect(()=>{
  const sync=(event:StorageEvent)=>{if(event.key===LANGUAGE_KEY)setLanguage(valid(event.newValue)?event.newValue:'en');};
  window.addEventListener('storage',sync);return()=>window.removeEventListener('storage',sync);
 },[]);
 return {language,setLanguage,t:((text:string,error=false)=>translate(language,text,error)) as Translate};
}

export function LanguageSelector({language,onChange,t}:{language:Language;onChange:(language:Language)=>void;t:Translate}){
 return <label className="language-selector"><Globe className="language-globe" size={16} aria-hidden="true"/><span className="visually-hidden">{t('Language')}</span><select aria-label={t('Choose language')} value={language} onChange={event=>{if(valid(event.target.value))onChange(event.target.value);}}>{Object.entries(languages).map(([value,label])=><option key={value} value={value} lang={value}>{label}</option>)}</select><ChevronDown className="language-chevron" size={14} aria-hidden="true"/></label>;
}
