import SearchBar from "./SearchBar";
import {
Users,
MessageCircle,
GraduationCap
} from "lucide-react";


export default function Hero(){


const stats=[

{
icon:Users,
number:"1.200+",
text:"Hoca"
},

{
icon:MessageCircle,
number:"8.000+",
text:"Yorum"
},

{
icon:GraduationCap,
number:"20+",
text:"Bölüm"
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