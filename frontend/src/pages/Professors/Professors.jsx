import {useEffect,useState} from "react";

import {
getProfessors
} from "../../api/professors";

import Card from "../../components/Card";

import {
Link
} from "react-router-dom";


export default function Professors(){


const [professors,setProfessors]=useState([]);



useEffect(()=>{

getProfessors()

.then(res=>{

setProfessors(res.data.items);

})

.catch(()=>{});


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

Hocalar

</h1>



<div className="
grid
md:grid-cols-2
lg:grid-cols-3
gap-6
">


{

professors.map((professor)=>(


<Link

key={professor.id}

to={`/hocalar/${professor.id}`}

>


<Card className="p-6">


<h2 className="
text-xl
font-semibold
">

{professor.name}

</h2>


<p className="
mt-2
text-gray-600
">

{professor.department?.name}

</p>


</Card>


</Link>


))


}


</div>


</section>

);

}