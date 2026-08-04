import {
useEffect,
useState
} from "react";

import {
useParams
} from "react-router-dom";


import {
getProfessor
} from "../../api/professors";


import Card from "../../components/Card";


export default function ProfessorDetail(){


const {id}=useParams();


const [professor,setProfessor]=useState(null);



useEffect(()=>{

getProfessor(id)

.then(res=>{

setProfessor(res.data);

});


},[id]);



if(!professor){

return (

<div className="p-20">

Yükleniyor...

</div>

)

}



return (

<section className="
max-w-[1200px]
mx-auto
px-6
py-16
">


<Card className="p-8">


<h1 className="
heading-font
text-5xl
">

{professor.name}

</h1>



<p className="mt-4">

{professor.department?.name}

</p>



</Card>


</section>

);


}