import {
useEffect,
useState
} from "react";


import {
getCourses
} from "../../api/courses";


import Card from "../../components/Card";


export default function Courses(){


const [courses,setCourses]=useState([]);



useEffect(()=>{

getCourses()

.then(res=>{

setCourses(res.data);

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

Dersler

</h1>



<div className="
grid
md:grid-cols-3
gap-6
">


{

courses.map(course=>(


<Card

key={course.id}

className="p-6"

>


<h2 className="text-xl font-semibold">

{course.name}

</h2>


<p className="text-gray-600 mt-2">

{course.code}

</p>


</Card>


))


}


</div>


</section>

);


}