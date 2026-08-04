import {
Search
} from "lucide-react";


export default function SearchBar(){


return (

<div

className="
flex
w-full
max-w-[600px]
border
border-[#102744]
bg-white
"

>


<div

className="
flex
items-center
gap-3
px-5
flex-1
"

>


<Search size={20}/>



<input

type="text"

placeholder="Hoca, ders veya bölüm ara..."

className="
outline-none
w-full
bg-transparent
text-sm
"

 />


</div>



<button

className="
bg-[#102744]
text-white
px-8
text-sm
"

>

Ara

</button>


</div>


);

}