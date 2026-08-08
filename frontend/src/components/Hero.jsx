import { useEffect, useState } from "react";

import SearchBar from "./SearchBar";
import {
Users,
MessageCircle,
GraduationCap
} from "lucide-react";

import { getUniversities } from "../api/universities";
import { getProfessors } from "../api/professors";
import { getReviews } from "../api/reviews";


export default function Hero(){


const [sayilar,setSayilar]=useState({
universite:null,
hoca:null,
yorum:null
});


// Ana sayfa kritik değil: istek hata verirse sayı "—" kalır, ekranda hata gösterilmez.
useEffect(()=>{

let iptal=false;

const oku=(istek,alan)=>istek
.then((res)=>{
if(!iptal){
setSayilar((onceki)=>({...onceki,[alan]:res.data.total}));
}
})
.catch(()=>{});

oku(getUniversities({limit:1}),"universite");
oku(getProfessors({limit:1}),"hoca");
oku(getReviews({limit:1}),"yorum");

return ()=>{
iptal=true;
};

},[]);


const bicimle=(deger)=>deger===null?"—":deger.toLocaleString("tr-TR");


const stats=[

{
icon:GraduationCap,
number:bicimle(sayilar.universite),
text:"Üniversite"
},

{
icon:Users,
number:bicimle(sayilar.hoca),
text:"Hoca"
},

{
icon:MessageCircle,
number:bicimle(sayilar.yorum),
text:"Yorum"
}

];


return (

<section

className="
pt-20
pb-20
"

>


<div

className="
max-w-[650px]
"

>


<h1

className="
heading-font
text-5xl
md:text-6xl
leading-tight
font-bold
"

>

Doğru hocayı seç,
gerçek öğrenci deneyimlerini keşfet.

</h1>



<p

className="
mt-6
text-gray-600
leading-relaxed
text-lg
"

>

Kürsü, öğrencilerin dersler ve akademisyenler
hakkındaki deneyimlerini paylaştığı
anonim değerlendirme platformudur.

</p>



<p

className="
mt-6
rounded-lg
border
border-amber-300
bg-amber-50
px-4
py-3
text-sm
text-amber-900
"

>

Demo sürümü — akademisyen isimleri gerçek değildir,
örnek veriyle üretilmiştir.

</p>



<div

className="
mt-10
"

>

<SearchBar/>

</div>



</div>



<div

className="
mt-14
flex
flex-wrap
gap-10
"

>


{

stats.map((item,index)=>{


const Icon=item.icon;


return (

<div

key={index}

className="
flex
items-center
gap-4
"

>


<Icon size={30}/>


<div>

<p

className="
text-2xl
font-semibold
"

>

{item.number}

</p>


<p

className="
text-sm
text-gray-600
"

>

{item.text}

</p>


</div>


</div>

);


})


}


</div>



</section>

);

}