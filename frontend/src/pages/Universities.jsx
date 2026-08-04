import {
useEffect,
useState
} from "react";


import {
getUniversities
} from "../api/universities";


import Card from "../components/Card";


export default function Universities(){


const [universities,setUniversities]=useState([]);



useEffect(()=>{


getUniversities()

.then(res=>{

setUniversities(res.data.items);

});


},[]);



return (

<section className="
max-w-[1200px]
mx-auto
px-6
py-16
">


<h1 className="
heading-font
text-5xl
mb-10
">

Üniversiteler

</h1>



<div className="
grid
md:grid-cols-3
gap-6
">


{

universities.map(item=>(


<Card

key={item.id}

className="p-6"

>


<h2 className="text-xl font-semibold">

{item.name}

</h2>


</Card>


))


}


</div>


</section>

);


}