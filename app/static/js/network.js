document.addEventListener('DOMContentLoaded', () => {
 const selector=document.getElementById('network-request'), message=document.getElementById('network-message'), svg=document.getElementById('network-visual'), ns='http://www.w3.org/2000/svg';
 function el(tag,attrs={},text=''){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text)e.textContent=text;return e}
 function node(x,y,title,subtitle,kind){const g=el('g',{class:'network-node '+kind});g.append(el('rect',{x,y,width:176,height:66,rx:14}),el('text',{x:x+14,y:y+27,class:'node-title'},title),el('text',{x:x+14,y:y+48,class:'node-subtitle'},subtitle));svg.appendChild(g)}
 function uniqueDonors(input){const seen=new Set();return (input||[]).filter(d=>{const id=d.donor_id;if(id===null||id===undefined||seen.has(id))return false;seen.add(id);return true})}
 function rankBadge(rank){return rank===1?'🥇 Rank #1':rank===2?'🥈 Rank #2':rank===3?'🥉 Rank #3':'#'+rank}
 function donorNode(x,y,donor){
  const rank=donor.rank||'—',rankClass=rank<=3?' rank-'+rank:' rank-other';
  const groupCity=[donor.blood_group||'N/A',donor.city||'Location not set'].join(' · ');
  const distance=donor.distance_km===null||donor.distance_km===undefined?'N/A':Number(donor.distance_km).toFixed(2)+' km';
  const score=donor.ai_score===null||donor.ai_score===undefined?'N/A':Number(donor.ai_score).toFixed(2);
  const match=donor.match_level===0?'Exact match · Level 0':'Compatible · Level '+donor.match_level;
  const g=el('g',{class:'network-node donor'+rankClass});
  g.append(
   el('rect',{x,y,width:252,height:132,rx:14}),
   el('text',{x:x+12,y:y+20,class:'node-rank'},rankBadge(rank)),
   el('text',{x:x+12,y:y+43,class:'node-title'},truncate(donor.name||'Donor',29)),
   el('text',{x:x+12,y:y+64,class:'node-subtitle'},truncate(groupCity,31)),
   el('text',{x:x+12,y:y+86,class:'node-subtitle'},'Shortest distance: '+distance),
   el('text',{x:x+12,y:y+108,class:'node-subtitle'},'Score '+score+' · '+match)
  );
  svg.appendChild(g)
 }
 function truncate(value,max){return value.length>max?value.slice(0,max-1)+'…':value}
 function graph(data){
  svg.replaceChildren();
  const req=data.selected_request;
  if(!req){svg.setAttribute('viewBox','0 0 930 250');svg.appendChild(el('text',{x:30,y:60,class:'graph-empty'},'No active request is available.'));return}
  const donors=uniqueDonors(data.donors),compatible=Object.entries(data.compatibility||{}).filter(([,rs])=>rs.includes(req.blood_group)).map(([g])=>g),visible=compatible.length?compatible:[req.blood_group];
  const height=Math.max(340,donors.length*150+80,visible.length*88+100);
  svg.setAttribute('viewBox','0 0 930 '+height);svg.setAttribute('preserveAspectRatio','xMinYMin meet');
  const rx=28,ry=height/2-33,gx=310,dx=640,ys=new Map();
  visible.forEach((group,index)=>ys.set(group,40+index*88));
  visible.forEach(group=>{const y=ys.get(group);svg.appendChild(el('line',{x1:rx+176,y1:ry+33,x2:gx,y2:y+33,class:'graph-edge request-edge'}));node(gx,y,group,'compatible donor group','blood')});
  donors.forEach(donor=>{const y=22+((donor.rank||1)-1)*150,groupY=ys.get(donor.blood_group)||ry;svg.appendChild(el('line',{x1:gx+176,y1:groupY+33,x2:dx,y2:y+66,class:'graph-edge donor-edge'}));donorNode(dx,y,donor)});
  node(rx,ry,'Request #'+req.request_id,req.blood_group+' · '+req.urgency_level,'request')
 }
 function groups(data){const box=document.getElementById('network-groups');box.replaceChildren();const recipient=data.selected_request?.blood_group, compatible=new Set(Object.entries(data.compatibility||{}).filter(([,rs])=>rs.includes(recipient)).map(([g])=>g));(data.blood_groups||[]).forEach(g=>{const chip=document.createElement('span');chip.className='blood-group-node '+(g===recipient?'is-request':compatible.has(g)?'is-compatible':'');chip.textContent=g;box.appendChild(chip)})}
 function donors(data){
  const box=document.getElementById('network-donors');box.replaceChildren();
  const donorList=uniqueDonors(data.donors);
  if(!donorList.length){const p=document.createElement('p');p.className='network-empty';p.textContent=data.selected_request?'No available, eligible donors match this request yet.':'Select an active request to discover donors.';box.appendChild(p);return}
  donorList.forEach(d=>{
   const c=document.createElement('article'),rank=d.rank||'—';c.className='network-donor-card network-rank-'+(rank<=3?rank:'other');
   const rankBadgeElement=document.createElement('span');rankBadgeElement.className='network-rank-badge';rankBadgeElement.textContent=rankBadge(rank);
   const h=document.createElement('h3');h.textContent=d.name||'Donor';
   const bloodCity=document.createElement('p');bloodCity.className='network-donor-meta';bloodCity.textContent=(d.blood_group||'N/A')+' · '+(d.city||'Location not set');
   const route=document.createElement('p');route.className='network-route';route.textContent=d.distance_km===null||d.distance_km===undefined?'Shortest distance: unavailable (coordinates missing)':'Shortest distance: '+Number(d.distance_km).toFixed(2)+' km';
   const reliability=document.createElement('p');reliability.className='network-score';reliability.textContent='Reliability: '+(d.reliability_score===null||d.reliability_score===undefined?'N/A':d.reliability_score+'/100');
   const score=document.createElement('p');score.className='network-score';score.textContent='Score: '+(d.ai_score===null||d.ai_score===undefined?'N/A':Number(d.ai_score).toFixed(2));
   const match=document.createElement('p');match.className='network-match-level';match.textContent=(d.match_level===0?'Exact match':'Compatible')+' · Level '+d.match_level;
   const why=document.createElement('p');why.className='network-why';why.textContent='Why recommended: '+((d.why_recommended||[]).join(' · ')||'No additional matching details available.');
   c.append(rankBadgeElement,h,bloodCity,route,reliability,score,match,why);box.appendChild(c)
  })
 }
 async function load(){if(!selector?.value){message.textContent='No active blood requests are available for this account.';message.className='network-message is-empty';graph({});donors({});return}message.textContent='Building graph and discovering matches…';try{const res=await fetch(`/api/network?request_id=${encodeURIComponent(selector.value)}`),data=await res.json();if(!res.ok)throw new Error(data.error||'Unable to load network.');message.textContent=data.donors.length+' compatible donors found. Ranked using blood-group compatibility, shortest Dijkstra distance, reliability and request urgency.';message.className='network-message is-success';document.getElementById('network-group-count').textContent=data.blood_groups.length;document.getElementById('network-donor-count').textContent=data.donors.length;document.getElementById('network-edge-count').textContent=data.edges.length;graph(data);groups(data);donors(data);const best=data.donors.filter(d=>d.route_available).sort((a,b)=>a.route_distance_km-b.route_distance_km)[0];document.getElementById('network-route-summary').textContent=best?`Shortest route: ${(best.route_labels||[]).join(' → ')} · ${best.route_distance_km.toFixed(2)} km.`:'No coordinate-backed route is available for this request.'}catch(e){message.textContent=e.message;message.className='network-message is-error'}}

 async function loadHasse(){
  const target=document.getElementById('hasse-svg'), status=document.getElementById('hasse-status');
  try{
   const response=await fetch('/api/compatibility/order'), data=await response.json();
   if(!response.ok) throw new Error(data.error||'Unable to load the Hasse diagram.');
   target.replaceChildren();
   const width=720,height=470,depths={};
   (data.nodes||[]).forEach(group=>depths[group]=group===data.minimal_element?0:-1);
   for(let pass=0;pass<(data.nodes||[]).length;pass++){
    (data.cover_edges||[]).forEach(edge=>{
     if(depths[edge.source]>=0) depths[edge.target]=Math.max(depths[edge.target],depths[edge.source]+1);
    });
   }
   const layers={};
   Object.keys(depths).forEach(group=>{const d=Math.max(0,depths[group]);(layers[d]||(layers[d]=[])).push(group)});
   Object.values(layers).forEach(layer=>layer.sort());
   const maxDepth=Math.max(...Object.keys(layers).map(Number)), positions={};
   target.setAttribute('viewBox','0 0 '+width+' '+height);
   const defs=el('defs'), marker=el('marker',{id:'hasse-arrow',markerWidth:8,markerHeight:8,refX:6,refY:3,orient:'auto',markerUnits:'strokeWidth'});
   marker.appendChild(el('path',{d:'M0,0 L0,6 L7,3 z',class:'hasse-arrowhead'}));defs.appendChild(marker);target.appendChild(defs);
   Object.entries(layers).forEach(([depth,layer])=>{
    layer.forEach((group,index)=>{positions[group]={x:width*(index+1)/(layer.length+1),y:height-55-(Number(depth)*115)}});
   });
   (data.cover_edges||[]).forEach(edge=>{
    const a=positions[edge.source],b=positions[edge.target];
    if(a&&b) target.appendChild(el('line',{x1:a.x,y1:a.y-23,x2:b.x,y2:b.y+24,class:'hasse-edge','marker-end':'url(#hasse-arrow)'}));
   });
   Object.entries(positions).forEach(([group,pos])=>{
    target.appendChild(el('circle',{cx:pos.x,cy:pos.y,r:25,class:'hasse-node'}));
    target.appendChild(el('text',{x:pos.x,y:pos.y+5,class:'hasse-label','text-anchor':'middle'},group));
   });
   status.textContent='Partial order checks: reflexive '+data.reflexive+', antisymmetric '+data.antisymmetric+', transitive '+data.transitive+'. Minimal: '+data.minimal_element+' · Maximal: '+data.maximal_element+' · Cover edges: '+data.cover_edges.length+'.';
  }catch(error){status.textContent=error.message}
 }
 function renderAssignments(data){
  const box=document.getElementById('network-assignments');box.replaceChildren();
  (data.assignments||[]).forEach(item=>{
   const row=document.createElement('article');row.className='network-assignment';
   const title=document.createElement('strong');title.textContent='#'+item.request.request_id+' · '+item.request.blood_group+' · '+item.request.urgency_level;
   const value=document.createElement('span');
   value.textContent=item.donor?item.donor.name+' · '+item.donor.blood_group+' · '+(item.donor.is_verified?'Verified':'Not verified')+' · '+(item.donor.donation_count||0)+' donation(s)':'Assigned donor (identity hidden)';
   row.append(title,value);box.appendChild(row);
  });
  (data.unmatched_requests||[]).forEach(item=>{
   const row=document.createElement('article');row.className='network-assignment is-unmatched';
   const title=document.createElement('strong');title.textContent='#'+item.request.request_id+' · '+item.request.blood_group+' · unmatched';
   const reason=document.createElement('p');reason.textContent=item.hall_explanation;
   row.append(title,reason);box.appendChild(row);
  });
  if(!box.children.length){const empty=document.createElement('p');empty.className='network-empty';empty.textContent='There are no active requests to assign.';box.appendChild(empty)}
 }
 async function loadAssignments(){
  const box=document.getElementById('network-assignments');box.textContent='Calculating global assignments…';
  try{
   const response=await fetch('/api/assign'),data=await response.json();
   if(!response.ok)throw new Error(data.error||'Unable to load assignments.');
   renderAssignments(data)
  }catch(error){box.textContent=error.message}
 }


 async function loadFacilities(){
  const hospitalsBox=document.getElementById('hospital-directory');
  const banksBox=document.getElementById('blood-bank-directory');
  try{
   const [hospitalsResponse,banksResponse]=await Promise.all([fetch('/api/hospitals'),fetch('/api/blood-banks')]);
   const [hospitalsData,banksData]=await Promise.all([hospitalsResponse.json(),banksResponse.json()]);
   if(!hospitalsResponse.ok||!banksResponse.ok)throw new Error('Unable to load the facility directory.');
   hospitalsBox.replaceChildren();
   (hospitalsData.hospitals||[]).forEach(hospital=>{
    const card=document.createElement('article');card.className='facility-card';
    const heading=document.createElement('h3');heading.textContent=hospital.name;
    const city=document.createElement('p');city.textContent=hospital.city||'City not listed';
    const address=document.createElement('p');address.textContent=hospital.address||'Address not listed';
    const phone=document.createElement('p');phone.textContent=hospital.phone?'Contact: '+hospital.phone:'Contact not listed';
    card.append(heading,city,address,phone);
    if(hospital.is_demo){const tag=document.createElement('span');tag.className='facility-demo-tag';tag.textContent='Demo record';card.appendChild(tag)}
    hospitalsBox.appendChild(card);
   });
   if(!hospitalsBox.children.length){const empty=document.createElement('p');empty.className='network-empty';empty.textContent='No hospitals are listed yet.';hospitalsBox.appendChild(empty)}
   banksBox.replaceChildren();
   (banksData.blood_banks||[]).forEach(bank=>{
    const card=document.createElement('article');card.className='facility-card';
    const heading=document.createElement('h3');heading.textContent=bank.name;
    const city=document.createElement('p');city.textContent=bank.city||'City not listed';
    const address=document.createElement('p');address.textContent=bank.address||'Address not listed';
    const phone=document.createElement('p');phone.textContent=bank.phone?'Contact: '+bank.phone:'Contact not listed';
    const inventory=document.createElement('div');inventory.className='facility-inventory';
    (bank.inventory||[]).forEach(item=>{
     const row=document.createElement('span');
     row.textContent=item.blood_group+': '+item.units+(item.is_demo?' sample units':' recorded units');
     inventory.appendChild(row);
    });
    if(!inventory.children.length){const empty=document.createElement('span');empty.textContent='No inventory records';inventory.appendChild(empty)}
    card.append(heading,city,address,phone,inventory);
    if(bank.is_demo){const tag=document.createElement('span');tag.className='facility-demo-tag';tag.textContent='Demo record';card.appendChild(tag)}
    banksBox.appendChild(card);
   });
   if(!banksBox.children.length){const empty=document.createElement('p');empty.className='network-empty';empty.textContent='No blood banks are listed yet.';banksBox.appendChild(empty)}
  }catch(error){hospitalsBox.textContent=error.message;banksBox.textContent=error.message}
 }
 selector?.addEventListener('change',load);document.getElementById('logout-btn')?.addEventListener('click',async()=>{await fetch('/api/logout',{method:'POST'});location.href='/login'});document.getElementById('refresh-assignments')?.addEventListener('click',loadAssignments);load();loadHasse();loadAssignments();loadFacilities()
});
