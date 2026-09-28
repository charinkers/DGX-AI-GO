const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function el(){return {children:[],style:{},classList:{add(){},remove(){}},setAttribute(){},appendChild(x){this.children.push(x)},querySelectorAll(){return []},value:'',checked:false,innerHTML:'',textContent:''};}
function context(){return vm.createContext({document:{getElementById(id){if(!elements.has(id))elements.set(id,el());return elements.get(id)},createElement:el},location:{protocol:'http:',origin:'http://localhost:8090'},localStorage:{getItem(){return 'a'.repeat(64)},setItem(){}},crypto:{randomUUID(){return 'random-id'}},fetch(){return new Promise(()=>{})},alert(){},console,Date});}
const html=fs.readFileSync('web-preview/index.html','utf8');
const ctx=context();vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
const contract=vm.runInContext('buildContract()',ctx);
assert.equal(typeof contract.battery,'number');
assert.equal(contract.personality.trait,'lively');
assert.equal(contract.safety.content_filter,true);
elements.get('export').onclick();
assert.deepEqual(JSON.parse(elements.get('cfg').textContent),JSON.parse(JSON.stringify(contract)));
assert.equal(vm.runInContext('thumbColor({color:"red;\\\" onerror=alert(1)"})',ctx),'#534AB7');
const payload='<img src=x onerror=alert(1)>';
assert(!vm.runInContext(`escapeHtml(${JSON.stringify(payload)})`,ctx).includes('<img'));
const server=fs.readFileSync('community/server.py','utf8');
const gallery=context();vm.runInContext(server.match(/<script>([\s\S]*?)<\/script>/)[1],gallery);
assert(!vm.runInContext(`esc(${JSON.stringify(payload)})`,gallery).includes('<img'));
assert.equal(vm.runInContext('color("red; background:url(x)")',gallery),'#cccccc');
console.log(JSON.stringify(contract));
