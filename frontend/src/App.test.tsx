import {render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, expect, test, vi} from 'vitest';
import App from './App';

afterEach(()=>{vi.unstubAllGlobals();localStorage.clear();});
function backend(fail=false){
 const conversation={id:'c1',title:'Duplicate payment · Order #5841',external_reference:'demo:billing:5841',status:'New',priority:'High',assignee:'Alex Morgan',updated_at:'2026-10-06T10:00:00Z',created_at:'2026-10-06T10:00:00Z',sla_state:'At risk',sla_target_minutes:120,sla_due_at:'2026-10-06T12:00:00Z',sla_closed:false};
 const messages=[{id:'m1',role:'user',content:'Charged twice for order #5841',created_at:conversation.created_at}];
 let analyses:any[]=[]; const events:any[]=[]; const calls:any[]=[];
 vi.stubGlobal('fetch',vi.fn(async(path:string,options:any)=>{
  const body=options.body?JSON.parse(options.body):undefined; calls.push([path,body]);
  if(fail)return {ok:false,json:async()=>({detail:'Backend unavailable'})};
  let data:any;
  if(path.startsWith('/api/v1/conversations?'))data=path.includes('missing')?[]:[conversation];
  else if(path==='/api/v1/conversations' )data=[conversation];
  else if(path==='/api/v1/conversations/c1'){Object.assign(conversation,body);data=conversation;}
  else if(path==='/api/v1/dashboard')data={total:1,open:1,resolved:0,mock_sends:0,priority_distribution:{High:1},intent_distribution:{'Billing issue':1},average_resolution_minutes:null};
  else if(path==='/api/v1/knowledge')data=[{id:'k1',key:'refund-policy-3.2',title:'Refund Policy §3.2',content:'Verify transactions'}];
  else if(path.startsWith('/api/v1/audit'))data=events;
  else if(path.endsWith('/timeline'))data=[...events].reverse();
  else if(path.endsWith('/notes')){events.push({id:'n'+events.length,action:'note.created',created_at:conversation.created_at,details:{content:body.content,author:body.author}});data=body;}
  else if(path.endsWith('/messages'))data=messages;
  else if(path.endsWith('/reply')){
   const result={...analyses[0].result,reply_content:body.content,reply_status:{edit:'draft',approve:'approved','mock-send':'sent'}[body.action as 'edit'|'approve'|'mock-send']};
   analyses=[{...analyses[0],result}]; data=analyses[0];
   events.push({id:'e'+events.length,action:'reply.'+body.action,entity_id:'a1',created_at:conversation.created_at,details:{content:body.content,synthetic:true}});
   if(body.action==='mock-send')messages.push({id:'m2',role:'assistant',content:body.content,created_at:conversation.created_at});
  }else if(path.endsWith('/analyses')){
   if(body)analyses=[{id:'a1',provider:'mock',created_at:conversation.created_at,result:{confidence:{intent:.96,priority:.9,sentiment:.78,kb_match:.95},explanations:{intent:'Matched charged twice',kb_match:'Exact refund policy key'},confidence_method:'Fixed mock rule scores',intent:'Billing issue',priority:'High',sentiment:'Negative',summary:'Duplicate payment',order_numbers:['5841'],knowledge_citations:['refund-policy-3.2'],suggested_reply:'Verify the duplicate payment.'}}];
   data=body?analyses[0]:analyses;
  }else throw new Error('Unexpected request: '+path);
  return {ok:true,json:async()=>structuredClone(data)};
 })); return calls;
}
test('Inbox → Conversation → AI Analysis → Edit → Approve → Mock Send → Audit, including remount persistence',async()=>{
 const calls=backend(); const user=userEvent.setup(); const view=render(<App/>);
 await user.click(await screen.findByRole('button',{name:/Alex Carter/}));
 await user.click(screen.getByRole('button',{name:'Conversation'}));
 expect(await screen.findByText('Charged twice for order #5841')).toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:'AI Analysis'}));
 await user.click(screen.getByRole('button',{name:/Analyze conversation/}));
 expect(await screen.findByText('Billing issue')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Mock Send'})).toBeDisabled();
 await user.click(screen.getByRole('button',{name:'Edit'}));
 await user.clear(screen.getByRole('textbox',{name:'Edit suggested reply'}));
 await user.type(screen.getByRole('textbox',{name:'Edit suggested reply'}),'Reviewed reply for #5841');
 await user.click(screen.getByRole('button',{name:'Save edits'}));
 await screen.findByText('Edits saved. Approval is required.');
 expect(screen.getByRole('button',{name:'Mock Send'})).toBeDisabled();
 await user.click(screen.getByRole('button',{name:'Approve'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Mock Send'})).toBeEnabled());
 await user.click(screen.getByRole('button',{name:'Mock Send'}));
 await screen.findByText('Mock sent');
 expect(screen.getByRole('button',{name:'Mock Send'})).toBeDisabled();
 await user.click(screen.getByRole('button',{name:'Audit'}));
 for(const action of ['edit','approve','mock-send'])expect(await screen.findByText('reply.'+action,{selector:'td span'})).toBeInTheDocument();
 expect(calls.filter(([path])=>path.endsWith('/reply')).map(([,body])=>body)).toEqual(['edit','approve','mock-send'].map(action=>({action,content:'Reviewed reply for #5841'})));
 view.unmount(); render(<App/>); await screen.findByText('Mock sent');
 expect(screen.getByRole('button',{name:'Edit'})).toBeDisabled();
});
test('initial backend failure hides empty hints and Retry restores conversation detail',async()=>{
 backend(true); const user=userEvent.setup();render(<App/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable');
 expect(screen.queryByText('Your demo workspace is ready.')).not.toBeInTheDocument();
 expect(screen.queryByText('No matching conversations.')).not.toBeInTheDocument();
 backend();await user.click(screen.getByRole('button',{name:'Retry'}));
 expect(await screen.findByText('Charged twice for order #5841')).toBeInTheDocument();
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('Inbox filters, empty search, status assignment and database dashboard',async()=>{
 backend();const user=userEvent.setup();render(<App/>);
 await screen.findByRole('button',{name:/Alex Carter/});
 await user.selectOptions(screen.getByLabelText('Filter status'),'Resolved');
 expect(screen.getByText('No matching conversations.')).toBeInTheDocument();
 await user.selectOptions(screen.getByLabelText('Filter status'),'');
 await user.selectOptions(screen.getByLabelText('Filter priority'),'Low');
 expect(screen.getByText('No matching conversations.')).toBeInTheDocument();
 await user.selectOptions(screen.getByLabelText('Filter priority'),'');
 await user.selectOptions(screen.getByLabelText('Conversation status'),'In review');
 await waitFor(()=>expect(screen.getByLabelText('Conversation status')).toHaveValue('In review'));
 await user.selectOptions(screen.getByLabelText('Conversation assignee'),'Sam Lee');
 await waitFor(()=>expect(screen.getByLabelText('Conversation assignee')).toHaveValue('Sam Lee'));
 await user.type(screen.getByLabelText('Search conversations'),'missing');
 await screen.findByText('No matching conversations.');
 await user.click(screen.getByRole('button',{name:'Dashboard'}));
 expect(screen.getByText('Priority distribution')).toBeInTheDocument();
 expect(screen.getByText('Intent distribution')).toBeInTheDocument();
});
test('Audit filters request conversation and action together',async()=>{
 const calls=backend();const user=userEvent.setup();render(<App/>);
 await screen.findByRole('button',{name:/Alex Carter/});
 await user.click(screen.getByRole('button',{name:'Audit'}));
 await user.selectOptions(screen.getByLabelText('Audit conversation'),'c1');
 await user.selectOptions(screen.getByLabelText('Audit action'),'reply.edit');
 await waitFor(()=>expect(calls.some(([path])=>path.includes('conversation_id=c1&action=reply.edit'))).toBe(true));
});

test('M3 SLA filter, assignment, status restrictions, notes, timeline and explainability persist',async()=>{
 const calls=backend();const user=userEvent.setup();const view=render(<App/>);
 await screen.findByRole('button',{name:/Alex Carter/});
 expect(screen.getByLabelText('Conversation status')).not.toHaveTextContent('Resolved');
 await user.selectOptions(screen.getByLabelText('Filter SLA'),'Overdue');
 expect(screen.getByText('No matching conversations.')).toBeInTheDocument();
 await user.selectOptions(screen.getByLabelText('Filter SLA'),'At risk');
 expect(screen.getByRole('button',{name:/Alex Carter/})).toBeInTheDocument();
 await user.selectOptions(screen.getByLabelText('Conversation status'),'In review');
 await waitFor(()=>expect(screen.getByLabelText('Conversation status')).toHaveValue('In review'));
 await user.selectOptions(screen.getByLabelText('Conversation assignee'),'Sam Lee');
 await waitFor(()=>expect(screen.getByLabelText('Conversation assignee')).toHaveValue('Sam Lee'));
 await user.selectOptions(screen.getByLabelText('Note author'),'Sam Lee');
 await user.type(screen.getByLabelText('Internal note'),'Verify both transactions before refund.');
 await user.click(screen.getByRole('button',{name:'Save internal note'}));
 await screen.findByText('Verify both transactions before refund.');
 expect(calls.some(([path,body])=>path.endsWith('/notes')&&body.author==='Sam Lee')).toBe(true);
 await user.click(screen.getByRole('button',{name:/Analyze conversation/}));
 expect(await screen.findByText('96%')).toBeInTheDocument();
 await user.click(screen.getByText('Why this analysis?'));
 expect(screen.getByText('Matched charged twice')).toBeInTheDocument();
 view.unmount();render(<App/>);
 expect(await screen.findByText('Verify both transactions before refund.')).toBeInTheDocument();
 expect(screen.getByLabelText('Conversation assignee')).toHaveValue('Sam Lee');
});

test.each([
 ['ru','Выбрать язык','Входящие','Обзор','База знаний','Журнал действий','Приоритет обращения','Низкий','Поиск правил','Определения показателей и охват'],
 ['uk','Вибрати мову','Вхідні','Огляд','База знань','Журнал дій','Пріоритет звернення','Низький','Пошук правил','Визначення показників і охоплення'],
])('language %s covers screens, keeps API values and persists across reload',async(lang,selector,inbox,dashboard,knowledge,audit,priority,low,search,definitions)=>{
 const calls=backend();const user=userEvent.setup();const view=render(<App/>);
 await screen.findByText('Charged twice for order #5841');
 await user.selectOptions(screen.getByRole('combobox',{name:'Choose language'}),lang);
 expect(document.documentElement.lang).toBe(lang);
 expect(localStorage.getItem('helixprimus.language')).toBe(lang);
 expect(screen.getByRole('button',{name:new RegExp('^'+inbox)})).toBeInTheDocument();
 expect(screen.getByRole('combobox',{name:selector})).toHaveValue(lang);
 expect(screen.getByRole('combobox',{name:priority})).toHaveTextContent(low);
 await user.selectOptions(screen.getByRole('combobox',{name:priority}),'Low');
 await waitFor(()=>expect(calls.some(([path,body])=>path==='/api/v1/conversations/c1'&&body?.priority==='Low')).toBe(true));
 expect(screen.getByText('Charged twice for order #5841')).toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:dashboard}));
 expect(screen.getByText(definitions)).toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:knowledge}));
 expect(screen.getByPlaceholderText(search)).toBeInTheDocument();
 expect(screen.getByText('Verify transactions')).toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:audit}));
 view.unmount();render(<App/>);
 expect(screen.getByRole('combobox',{name:selector})).toHaveValue(lang);
 expect(screen.getByRole('button',{name:new RegExp('^'+inbox)})).toBeInTheDocument();
 await screen.findByText('Charged twice for order #5841');
 await user.selectOptions(screen.getByRole('combobox',{name:selector}),'en');
 expect(screen.getByRole('button',{name:/^Inbox/})).toBeInTheDocument();
 expect(localStorage.getItem('helixprimus.language')).toBe('en');
});

test('localized analysis, reply workflow and audit preserve payloads and editable content',async()=>{
 localStorage.setItem('helixprimus.language','uk');const calls=backend();const user=userEvent.setup();render(<App/>);
 await screen.findByText('Charged twice for order #5841');
 await user.click(screen.getByRole('button',{name:/Аналізувати звернення/}));
 expect(await screen.findByText('Проблема з оплатою')).toBeInTheDocument();
 expect(screen.getByText('Негативний')).toBeInTheDocument();
 await user.click(screen.getByRole('button',{name:'Редагувати'}));
 await user.clear(screen.getByRole('textbox',{name:'Редагувати запропоновану відповідь'}));
 await user.type(screen.getByRole('textbox',{name:'Редагувати запропоновану відповідь'}),'Operator draft');
 await user.selectOptions(screen.getByRole('combobox',{name:'Вибрати мову'}),'ru');
 expect(screen.getByRole('textbox',{name:'Редактировать предлагаемый ответ'})).toHaveValue('Operator draft');
 await user.click(screen.getByRole('button',{name:'Сохранить изменения'}));
 await screen.findByText('Изменения сохранены. Требуется подтверждение.');
 await user.click(screen.getByRole('button',{name:'Подтвердить'}));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Тестовая отправка'})).toBeEnabled());
 await user.click(screen.getByRole('button',{name:'Тестовая отправка'}));
 await user.click(screen.getByRole('button',{name:'Журнал действий'}));
 expect(await screen.findByText('Тестовый ответ отправлен',{selector:'td span'})).toBeInTheDocument();
 expect(calls.filter(([path])=>path.endsWith('/reply')).map(([,body])=>body)).toEqual(['edit','approve','mock-send'].map(action=>({action,content:'Operator draft'})));
});

test('invalid saved language falls back to English; localized error recovers',async()=>{
 localStorage.setItem('helixprimus.language','xx');backend(true);const user=userEvent.setup();render(<App/>);
 expect(screen.getByRole('combobox',{name:'Choose language'})).toHaveValue('en');
 await screen.findByRole('alert');
 await user.selectOptions(screen.getByRole('combobox',{name:'Choose language'}),'ru');
 expect(screen.getByRole('alert')).toHaveTextContent('Backend недоступен');
 backend();await user.click(screen.getByRole('button',{name:'Повторить'}));
 await screen.findByText('Charged twice for order #5841');
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});



test('synthetic policies localize titles/content and support localized search without changing keys',async()=>{
 backend();const mockFetch=fetch;
 vi.stubGlobal('fetch',vi.fn(async(path:any,options:any)=>path==='/api/v1/knowledge'?{ok:true,json:async()=>[{id:'k1',key:'refund-policy-3.2',title:'Refund Policy §3.2',content:'Duplicate payments: verify both transactions before issuing a refund. Confirmed duplicates are refunded to the original method. Never promise a refund before verification.'}]}:mockFetch(path,options)));
 const user=userEvent.setup();render(<App/>);await screen.findByText('Charged twice for order #5841');
 await user.selectOptions(screen.getByRole('combobox',{name:'Choose language'}),'ru');
 await user.click(screen.getByRole('button',{name:'База знаний'}));
 await user.type(screen.getByPlaceholderText('Поиск правил'),'возврата');
 expect(screen.getByText('Правила возврата §3.2')).toBeInTheDocument();
 expect(screen.getByText(/Повторные платежи: проверьте обе транзакции/)).toBeInTheDocument();
 expect(screen.getByText('refund-policy-3.2')).toBeInTheDocument();
 await user.clear(screen.getByPlaceholderText('Поиск правил'));
 await user.selectOptions(screen.getByRole('combobox',{name:'Выбрать язык'}),'uk');
 await user.type(screen.getByPlaceholderText('Пошук правил'),'повернення');
 expect(screen.getByText('Правила повернення §3.2')).toBeInTheDocument();
 expect(screen.getByText(/Повторні платежі: перевірте обидві транзакції/)).toBeInTheDocument();
});


test.each([
 ['en','Dashboard','Try the demo','Open conversation #5841','What does HELIXPRIMUS do?','Conversation'],
 ['ru','Обзор','Попробовать демо','Открыть обращение #5841','Что делает HELIXPRIMUS?','Обращение'],
 ['uk','Огляд','Спробувати демо','Відкрити звернення #5841','Що робить HELIXPRIMUS?','Звернення'],
])('Dashboard guided demo localizes and navigates in %s after language reload',async(lang,dashboard,title,cta,about,detail)=>{
 const calls=backend();const user=userEvent.setup();let view=render(<App/>);
 await screen.findByText('Charged twice for order #5841');
 await user.selectOptions(screen.getByRole('combobox',{name:'Choose language'}),lang);
 view.unmount();view=render(<App/>);
 await screen.findByText('Charged twice for order #5841');
 expect(document.documentElement.lang).toBe(lang);
 expect(localStorage.getItem('helixprimus.language')).toBe(lang);
 await user.click(screen.getByRole('button',{name:dashboard}));
 const region=screen.getByRole('region',{name:title});
 expect(region.querySelectorAll('ol li')).toHaveLength(4);
 if(lang!=='en')expect(region).not.toHaveTextContent('Deterministic mock AI');
 await user.click(screen.getByText(about));
 expect(region.querySelector('details')).toHaveAttribute('open');
 await user.click(screen.getByRole('button',{name:cta}));
 await waitFor(()=>expect(screen.getByRole('button',{name:detail})).toHaveAttribute('aria-current','page'));
 expect(screen.getByText('Charged twice for order #5841')).toBeInTheDocument();
 expect(calls.some(([path])=>path==='/api/v1/conversations/c1/messages')).toBe(true);
 expect(calls.some(([path])=>path==='/api/v1/demo/m3')).toBe(false);
 expect(document.activeElement).toBe(document.getElementById('workspace-content'));
});

test('guided demo seeds missing sample and selects billing reference rather than another #5841',async()=>{
 backend();const mockFetch=fetch;let seeded=false;
 vi.stubGlobal('fetch',vi.fn(async(path:any,options:any)=>{
  if(path==='/api/v1/demo/m3'){seeded=true;return {ok:true,json:async()=>({})};}
  if(path==='/api/v1/conversations'&&!seeded)return {ok:true,json:async()=>[{id:'other',title:'Delivery #5841',external_reference:'demo:order:5841',created_at:'2026-10-06T10:00:00Z',status:'New',priority:'Low',assignee:'Alex Morgan'}]};
  if(path.includes('/other/'))return {ok:true,json:async()=>[]};
  return mockFetch(path,options);
 }));
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('button',{name:/Jordan Blake/});
 await waitFor(()=>expect(screen.queryByText('Working…',{selector:'.notice'})).not.toBeInTheDocument());
 await user.click(screen.getByRole('button',{name:'Dashboard'}));
 await user.click(screen.getByRole('button',{name:'Open conversation #5841'}));
 expect(await screen.findByText('Charged twice for order #5841')).toBeInTheDocument();
 expect(seeded).toBe(true);
 expect(screen.getByRole('button',{name:'Conversation'})).toHaveAttribute('aria-current','page');
});
