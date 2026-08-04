import {
useEffect,
useState
} from "react";

import {
getFaculties
} from "../api/faculties";

import Card from "../components/Card";


export default function Faculties(){


const [faculties,setFaculties]=useState([]);



useEffect(()=>{

getFaculties()

.then(res=>{

setFaculties(res.data.items);

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

Fakülteler

</h1>



<div className="
grid
md:grid-cols-3
gap-6
">


{

faculties.map(item=>(


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