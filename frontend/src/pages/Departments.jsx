import {
useEffect,
useState
} from "react";

import {
getDepartments
} from "../api/departments";

import Card from "../components/Card";


export default function Departments(){


const [departments,setDepartments]=useState([]);



useEffect(()=>{

getDepartments()

.then(res=>{

setDepartments(res.data.items);

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

Bölümler

</h1>



<div className="
grid
md:grid-cols-3
gap-6
">


{

departments.map(item=>(


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