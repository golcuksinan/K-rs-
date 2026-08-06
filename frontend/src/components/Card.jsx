export default function Card({

children,
className=""

}){


return (

<div

className={`
bg-[#fffdf8]
border
border-[#102744]
${className}
`}

>

{children}

</div>

);


}