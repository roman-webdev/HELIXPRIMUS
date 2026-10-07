import {expect,test,vi,afterEach} from 'vitest';
import {renderHook,act} from '@testing-library/react';
import {translate,useLanguage,LANGUAGE_KEY} from './i18n';
import dictionaries from './translations.json';
afterEach(()=>{vi.restoreAllMocks();localStorage.clear();});
test('both dictionaries have identical keys and nonempty translations',()=>{
 expect(Object.keys(dictionaries.ru)).toEqual(Object.keys(dictionaries.uk));
 for(const dictionary of Object.values(dictionaries))for(const value of Object.values(dictionary))expect(value.trim()).not.toBe('');
});
test('explanations localize structure, retain evidence and keys, unknown errors use localized fallback',()=>{
 expect(translate('ru','Matched customer phrases: charged twice. Ordered rules select this intent.')).toBe('Найдены фразы клиента: charged twice. Тема выбрана по упорядоченным правилам.');
 expect(translate('uk','Exact policy key for the selected intent: refund-policy-3.2')).toBe('Точний ключ правила для вибраної теми: refund-policy-3.2');
 expect(translate('uk','Unknown server error',true)).toBe('Не вдалося виконати запит');
 expect(translate('ru','Alex Morgan')).toBe('Alex Morgan');
});
test('blocked storage does not prevent changing language',()=>{
 vi.spyOn(Storage.prototype,'getItem').mockImplementation(()=>{throw new Error('blocked');});
 vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('blocked');});
 const {result}=renderHook(useLanguage);
 expect(result.current.language).toBe('en');
 act(()=>result.current.setLanguage('uk'));
 expect(result.current.t('Inbox')).toBe('Вхідні');
 expect(document.documentElement.lang).toBe('uk');
});
test('language follows valid storage changes from another tab',()=>{
 const {result}=renderHook(useLanguage);
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:LANGUAGE_KEY,newValue:'ru'})));
 expect(result.current.language).toBe('ru');
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:LANGUAGE_KEY,newValue:'invalid'})));
 expect(result.current.language).toBe('en');
});
